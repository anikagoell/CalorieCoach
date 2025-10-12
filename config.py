import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    # Database
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(BASE_DIR, 'meals.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Secret key for session management
    SECRET_KEY = os.environ.get('SECRET_KEY', 'your-default-secret-key')

    # ML model paths
    CALORIE_MODEL_PATH = os.path.join(BASE_DIR, 'ml_models', 'calorie_predictor.pkl')
    MEAL_MODEL_PATH = os.path.join(BASE_DIR, 'ml_models', 'meal_recommender.pkl')

    # Optional: debug flag
    DEBUG = True
