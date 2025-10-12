from database import db
from datetime import datetime

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True)
    password_hash = db.Column(db.String(128))
    age = db.Column(db.Integer)
    gender = db.Column(db.String(10))
    weight = db.Column(db.Float)
    height = db.Column(db.Float)
    activity_level = db.Column(db.String(50))
    health_goal = db.Column(db.String(50))
    medical_conditions = db.Column(db.String(500))
    dietary_preference = db.Column(db.String(50))
    allergies = db.Column(db.String(500))

class Meal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    meal_type = db.Column(db.String(50))
    food_items = db.Column(db.String(1000))  # JSON string
    calories = db.Column(db.Integer)
    carbs = db.Column(db.Float)
    protein = db.Column(db.Float)
    fats = db.Column(db.Float)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
