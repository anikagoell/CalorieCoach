import pandas as pd
from app import db, app, Food

df = pd.read_csv("indian_food_nutrition.csv")

with app.app_context():
    for _, row in df.iterrows():
        name = row['Dish Name'].strip().lower()

        # ✅ Skip duplicate names already in database
        if Food.query.filter_by(name=name).first():
            continue

        food = Food(
            name=name,
            calories=row['Calories (kcal)'],
            carbs=row['Carbohydrates (g)'],
            protein=row['Protein (g)'],
            fat=row['Fats (g)']
        )
        db.session.add(food)

    db.session.commit()
    print("✅ Food database imported successfully (duplicates ignored)!")
