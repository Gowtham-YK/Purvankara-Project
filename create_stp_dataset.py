import json
import random
import os

# Set seed for reproducibility
random.seed(42)

# -----------------------------
# 1️⃣ List of Major Bangalore STPs
# -----------------------------
stp_list = [
    ("Vrishabhavathi Valley STP", 12.9547, 77.5200, 150),
    ("K&C Valley STP", 12.9700, 77.6300, 248),
    ("Hebbal STP", 13.0358, 77.5950, 100),
    ("Koramangala STP", 12.9352, 77.6245, 60),
    ("Bellandur STP", 12.9250, 77.6700, 90),
    ("Yelahanka STP", 13.1100, 77.5900, 80),
    ("Jakkur STP", 13.0675, 77.6092, 10),
    ("Kadubeesanahalli STP", 12.9390, 77.6920, 75),
    ("Hulimavu STP", 12.8850, 77.6000, 40),
    ("Challaghatta STP", 12.9200, 77.7000, 50),
    ("Nagawara STP", 13.0450, 77.6200, 70),
    ("Mailasandra STP", 12.9100, 77.5000, 30),
    ("Kengeri STP", 12.9100, 77.4800, 35),
    ("Madiwala STP", 12.9200, 77.6200, 45),
    ("Domlur STP", 12.9600, 77.6400, 25)
]

# -----------------------------
# 2️⃣ Create JSON Structure
# -----------------------------
stps_data = []

for i, (name, lat, lon, total_capacity) in enumerate(stp_list, start=1):

    current_load = round(total_capacity * random.uniform(0.3, 0.7), 2)
    available_capacity = round(total_capacity - current_load, 2)

    treatment_cost = round(random.uniform(5, 12), 2)

    stps_data.append({
    "stp_id": f"STP{i:03}",
    "stp_name": name,
    "latitude": lat,
    "longitude": lon,
    "total_capacity_mld": total_capacity,
    "current_load_mld": current_load,
    "available_capacity_mld": available_capacity,
    "treatment_cost_per_kl": treatment_cost
    })

# Final JSON format (compatible with Flask app)
final_data = {
    "places": [],   # You can later add geocoding places here
    "stps": stps_data
}

# -----------------------------
# 3️⃣ Save JSON File
# -----------------------------
output_path = os.path.join("data", "stp_data.json")

# Make sure data folder exists
os.makedirs("data", exist_ok=True)

with open(output_path, "w") as f:
    json.dump(final_data, f, indent=4)

print("stp_data.json created successfully!")
print(f"Saved at: {output_path}")
