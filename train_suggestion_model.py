import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
import pickle

# Load data
df = pd.read_csv("indian_food_nutrition.csv")

# Clean and standardize
df.columns = df.columns.str.strip()
features = ['Calories (kcal)', 'Carbohydrates (g)', 'Protein (g)', 'Fats (g)']
X = df[features].fillna(0)

# Scale the data
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# Cluster foods based on nutritional similarity
kmeans = KMeans(n_clusters=8, random_state=42, n_init=10)
df["Cluster"] = kmeans.fit_predict(X_scaled)

model_data = {
    "model": kmeans,
    "scaler": scaler,
    "df": df
}

with open("suggestion_model.pkl", "wb") as f:
    pickle.dump(model_data, f)


print("✅ Cluster-based suggestion model trained and saved!")
print(df.groupby("Cluster")[features].mean())
