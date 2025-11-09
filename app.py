from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from database import db, init_db
from models import User, Meal , Food
from werkzeug.utils import secure_filename
from sqlalchemy import func
from datetime import datetime, timedelta
import os, re, joblib, pickle
import numpy as np

def calculate_nutrition_from_db(meal_text):
    foods = re.split(",|and", meal_text.lower())
    total = {"calories": 0, "protein": 0, "carbs": 0, "fat": 0}
    unmatched_items = []

    for item in foods:
        item = item.strip()
        match = re.match(r"(\d+)\s*(.*)", item)
        qty, name = (1, item) if not match else (int(match.group(1)), match.group(2).strip())

        food = Food.query.filter(Food.name.ilike(f"%{name}%")).first()
        if food:
            total["calories"] += food.calories * qty
            total["protein"] += food.protein * qty
            total["carbs"] += food.carbs * qty
            total["fat"] += food.fat * qty
        else:
            unmatched_items.append(name)

    total["unmatched"] = unmatched_items
    return total


app = Flask(__name__)
app.config.from_object('config.Config')
app.secret_key = app.config['SECRET_KEY']

UPLOAD_FOLDER = 'static/profile_pics'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Initialize DB
init_db(app)

model_data_cache = None

# ---------- ROUTES ----------

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/home')
def home():
    return render_template('home.html')

@app.route('/profile')
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])

    if request.method == 'POST':
        file = request.files.get('profile_pic')
        if file and file.filename != '':
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            # save filename in DB
            user.profile_pic = filename
            db.session.commit()

    return render_template('profile.html', user=user)

@app.route('/bmi')
def bmi():
    return render_template('bmi.html')

@app.route('/water')
def water():
    return render_template('water.html')

@app.route('/report')
def report():
    return render_template('report.html')

    

# -------- Signup --------
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])

        # Check if email already exists
        if User.query.filter_by(email=email).first():
            return "Email already registered"

        user = User(name=name, email=email, password_hash=password)
        db.session.add(user)
        db.session.commit()

        session['user_id'] = user.id  # log in user
        return redirect(url_for('newuser_profile'))

    return render_template('signup.html')


# -------- Login --------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            return redirect(url_for('home'))
        else:
            error= "Invalid credentials"
            return render_template('login.html', error=error)

    return render_template('login.html')


# profile setup
@app.route('/newuser_profile', methods=['GET', 'POST'])
def newuser_profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])

    
    if request.method == 'POST':
        file = request.files.get('profile_pic')  
        if file and file.filename != '':
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            user.profile_pic = f"profile_pics/{filename}" 
        # Update profile details
        user.age = request.form.get('age')
        user.gender = request.form.get('gender')
        user.height = request.form.get('height')
        user.weight = request.form.get('weight')
        user.activity_level = request.form.get('activity_level')
        user.health_goal = request.form.get('goal')
        user.dietary_preference = request.form.get('diet_pref')
        user.medical_conditions = request.form.get('medical_conditions')
        user.allergies = request.form.get('allergies')
        user.units = request.form.get('units')
        user.bio = request.form.get('bio')
        
        db.session.commit()
        if all([user.name, user.age, user.gender]):  # basic check
            return render_template('profile.html', user=user)
        else:
            return render_template('home.html', user=user)
    
    return render_template('newuser.html', user=user)

@app.route('/log_meal', methods=['POST'])
def log_meal():
    if 'user_id' not in session:
        return jsonify({"status": "error", "message": "Not logged in"}), 401

    data = request.get_json()
    foods = data.get("foods", [])

    if not foods:
        return jsonify({"status": "error", "message": "No foods received"}), 400

    updated_foods = []
    total = {"calories": 0, "protein": 0, "carbs": 0, "fat": 0}

    for item in foods:
        name = item["name"].lower()
        qty = float(item["qty"])
        meal_type = item["meal"]

        food = Food.query.filter(Food.name.ilike(f"%{name}%")).first()

        if food:
            cal = food.calories * qty
            carb = food.carbs * qty
            protein = food.protein * qty
            fat = food.fat * qty
        else:
            cal = carb = protein = fat = 0  # food not found

        updated_foods.append({
            "name": item["name"],
            "meal": meal_type,
            "qty": qty,
            "cal": cal,
            "carb": carb,
            "protein": protein,
            "fat": fat
        })

        total["calories"] += cal
        total["carbs"] += carb
        total["protein"] += protein
        total["fat"] += fat

    # Load clustering model
    with open("suggestion_model.pkl", "rb") as f:
        scaler, kmeans, df = pickle.load(f)

    # Predict the cluster of the current meal
    cluster_input = [[total_calories, total_carbs, total_protein, total_fat]]
    cluster_id = int(kmeans.predict(scaler.transform(cluster_input))[0])

    # Save the meal with its cluster ID
    meal = Meal(
        user_id=session["user_id"],
        meal_text=meal_text,
        calories=total_calories,
        protein=total_protein,
        carbs=total_carbs,
        fat=total_fat,
        cluster_id=cluster_id  
        )
    
    db.session.add(meal)
    db.session.commit()


    return jsonify({"status": "success", "updatedFoods": updated_foods, "totals": total})

@app.route("/today_meals")
def today_meals():
    if 'user_id' not in session:
        return jsonify({"error": "Not logged in"}), 401

    today = datetime.utcnow().date()
    meals = Meal.query.filter(
        Meal.user_id == session['user_id'],
        db.func.date(Meal.date) == today
    ).all()

    formatted = []
    for m in meals:
        try:
            parsed = eval(m.meal_text) if isinstance(m.meal_text, str) else m.meal_text
            dish_names = ", ".join([f"{item['name']} (x{item['qty']})" for item in parsed])
        except Exception:
            dish_names = m.meal_text  # fallback in case eval fails

        formatted.append({
            "dish": dish_names,
            "calories": m.calories,
            "protein": m.protein,
            "carbs": m.carbs,
            "fat": m.fat
        })

    return jsonify({"meals": formatted})

@app.route("/suggest_meal", methods=["POST"])
def suggest_meal():
    import pickle, numpy as np, random, os
    from flask import jsonify, request
    global model_data_cache

    data = request.get_json()
    foods = data.get("foods", [])

    # --- Calculate totals ---
    total_cal = sum(f.get("cal", 0) for f in foods)
    total_protein = sum(f.get("protein", 0) for f in foods)
    total_carbs = sum(f.get("carb", 0) for f in foods)
    total_fat = sum(f.get("fat", 0) for f in foods)

    # --- Identify low nutrients ---
    low_nutrients = []
    if total_cal < 1500:
        low_nutrients.append("calories")
    if total_protein < 50:
        low_nutrients.append("protein")
    if total_carbs < 150:
        low_nutrients.append("carbs")
    if total_fat < 40:
        low_nutrients.append("fat")

    suggestion_text = "⚠️ Unable to generate meal suggestion right now."

    try:
        # ✅ Load model only once and reuse (cached)
        if model_data_cache is None:
            if os.path.exists("suggestion_model.pkl"):
                with open("suggestion_model.pkl", "rb") as f:
                    model_data_cache = pickle.load(f)
                app.logger.info("✅ Suggestion model loaded into cache.")
            else:
                app.logger.warning("⚠️ suggestion_model.pkl not found. Using fallback mode.")
                model_data_cache = None

        if model_data_cache:
            kmeans = model_data_cache["model"]
            scaler = model_data_cache["scaler"]
            df = model_data_cache["df"]

            # --- Predict user’s cluster ---
            user_features = np.array([[total_cal, total_carbs, total_protein, total_fat]])
            scaled = scaler.transform(user_features)
            cluster = kmeans.predict(scaled)[0]

            similar_meals = df[df["Cluster"] == cluster]
            if "Dish Name" in similar_meals.columns:
                suggestion = random.choice(similar_meals["Dish Name"].tolist())
            else:
                suggestion = random.choice(similar_meals.iloc[:, 0].tolist())



            # --- Feedback message ---
            if low_nutrients:
                feedback = f"Your {', '.join(low_nutrients)} intake seems low."
            else:
                feedback = "Your overall intake looks balanced. ✅"

            suggestion_text = f"{feedback} Try adding **{suggestion}** 🍽️"

        else:
            # --- Fallback when model not available ---
            if low_nutrients:
                fallback_suggestions = {
                    "calories": "rice, oats, or banana",
                    "protein": "eggs, paneer, dal, or chicken",
                    "carbs": "roti, fruits, or rice",
                    "fat": "nuts, olive oil, or seeds"
                }
                feedbacks = [f"{nutrient}: {fallback_suggestions[nutrient]}" for nutrient in low_nutrients]
                feedback_msg = "; ".join(feedbacks)
                suggestion_text = f"Your {', '.join(low_nutrients)} intake is low. Try adding: {feedback_msg} 🍴"
            else:
                suggestion_text = "Your intake looks balanced. Keep it up! ✅"

    except Exception as e:
        app.logger.warning(f"⚠️ Suggestion generation error: {e}")
        suggestion_text = f"⚠️ Unable to generate suggestion due to: {e}"

    return jsonify({
        "status": "success",
        "suggestion": suggestion_text,
        "totals": {
            "calories": total_cal,
            "protein": total_protein,
            "carbs": total_carbs,
            "fat": total_fat
        }
    })



# -------- Logout --------
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(debug=True)

