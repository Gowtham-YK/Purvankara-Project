import numpy as np
import random
import json
import os

np.random.seed(42)
random.seed(42)

# Bangalore zones (approximate coordinates)
zones = {
    "North": (13.1000, 77.6000),
    "South": (12.9000, 77.5800),
    "East": (12.9800, 77.6800),
    "West": (12.9600, 77.5000),
    "Central": (12.9700, 77.5900)
}

categories = {
    "Industry": (200, 1000),
    "Apartment": (50, 300),
    "Commercial": (100, 500),
    "Hospital": (150, 600),
    "Institution": (80, 400)
}

seasons = ["Summer", "Monsoon", "Winter"]

sellers_data = []

for i in range(1, 1001):  # 1000 synthetic sellers

    category = random.choice(list(categories.keys()))
    zone = random.choice(list(zones.keys()))

    base_lat, base_lon = zones[zone]

    latitude = base_lat + np.random.uniform(-0.02, 0.02)
    longitude = base_lon + np.random.uniform(-0.02, 0.02)

    population = np.random.randint(
        categories[category][0],
        categories[category][1]
    )

    per_capita_use = np.random.uniform(100, 180)
    water_consumption = population * per_capita_use

    wastewater_generated = water_consumption * 0.8 / 1000  # KL

    season = random.choice(seasons)

    # Seasonal multiplier
    if season == "Summer":
        wastewater_generated *= 1.1
    elif season == "Monsoon":
        wastewater_generated *= 0.95

    sellers_data.append({
        "seller_id": f"S{i:04}",
        "category": category,
        "zone": zone,
        "latitude": round(float(latitude), 6),
        "longitude": round(float(longitude), 6),
        "population": int(population),
        "water_consumption_lpd": round(float(water_consumption), 2),
        "wastewater_generated_kl": round(float(wastewater_generated), 2),
        "day_of_week": int(np.random.randint(0, 7)),
        "season": season
    })

# Final JSON structure
final_data = {
    "sellers": sellers_data
}

# Ensure data folder exists
os.makedirs("data", exist_ok=True)

output_path = os.path.join("data", "synthetic_sellers_data.json")

with open(output_path, "w") as f:
    json.dump(final_data, f, indent=4)

print("synthetic_sellers_data.json created successfully!")
print(f"Saved at: {output_path}")
