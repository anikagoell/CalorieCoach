from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from database import db, init_db
from models import User, Meal , Food
from werkzeug.utils import secure_filename
from sqlalchemy import func
from datetime import datetime, timedelta
import os
import re
from models import Food

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

    # ✅ Save combined meal to DB
    meal_entry = Meal(
        user_id=session['user_id'],
        meal_text=str(updated_foods),
        calories=total["calories"],
        protein=total["protein"],
        carbs=total["carbs"],
        fat=total["fat"]
    )
    db.session.add(meal_entry)
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
    data = request.get_json()
    foods = data.get("foods", [])

    total_cal = sum(f.get("cal", 0) for f in foods)
    total_protein = sum(f.get("protein", 0) for f in foods)
    total_carbs = sum(f.get("carb", 0) for f in foods)
    total_fat = sum(f.get("fat", 0) for f in foods)

    # ===== Simple rule-based logic (later replace with ML model) =====
    if total_cal < 1200:
        suggestion = "Your calorie intake is low today. Try adding healthy carbs like roti, oats, banana, or rice."
    elif total_protein < 50:
        suggestion = "Protein is low. Consider adding eggs, paneer, dal, sprouts, or chicken."
    elif total_cal > 2200:
        suggestion = "You crossed a high calorie limit today. Prefer lighter veggies and avoid sugar/fried items."
    elif total_fat > 70:
        suggestion = "Fat intake is high. Avoid fried foods and choose grilled or steamed options."
    else:
        suggestion = "Your diet looks well balanced so far. Keep it up! ✅"

    return jsonify({
        "status": "success",
        "suggestion": suggestion,
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

