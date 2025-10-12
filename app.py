from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from database import db, init_db
from models import User
from werkzeug.utils import secure_filename
import os

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
    return render_template('profile.html')

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


# -------- New User Profile --------
@app.route('/newuser_profile', methods=['GET', 'POST'])
def newuser_profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])

    
    if request.method == 'POST':
        file = request.files.get('profile_pic')  # match input name in form
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
        user.goal = request.form.get('goal')
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


# -------- Logout --------
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(debug=True)

