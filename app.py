from flask import Flask, jsonify, request, render_template, redirect, url_for
from flask import session
import json
import os
import math
import requests
import csv
from datetime import datetime, date
import osmnx as ox
import networkx as nx
from ml.predict_demand import predict_next_day, predict_week

app = Flask(__name__)

app.secret_key = "secret123"

# =========================================================
# LOAD ROAD NETWORK FOR A* ROUTING
# =========================================================
GRAPH_FILE = "bangalore_graph.graphml"

G = None

try:
    if os.path.exists(GRAPH_FILE):
        print("Loading saved road network...")
        G = ox.load_graphml(GRAPH_FILE)
    else:
        print("Skipping graph load (deployment)")
except Exception as e:
    print("Graph load skipped:", e)

print("Road network ready")

# =========================================================
# FILE PATHS
# =========================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

STP_FILE = os.path.join(BASE_DIR, "data", "stp_data.json")
STATUS_FILE = os.path.join(BASE_DIR, "data", "stp_status.json")
DATABASE_DIR = os.path.join(BASE_DIR, "database")
if not os.path.exists(DATABASE_DIR):
    os.makedirs(DATABASE_DIR)

# ✅ KEEP orders.csv INSIDE database/
ORDERS_FILE = os.path.join(DATABASE_DIR, "orders.csv")

# =========================================================
# ENSURE FILES EXIST
# =========================================================
if not os.path.exists(STATUS_FILE):
    with open(STATUS_FILE, "w") as f:
        json.dump({}, f)

if not os.path.exists(ORDERS_FILE):
    with open(ORDERS_FILE, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "order_id",
            "stp_id",
            "stp_name",
            "quantity_kld",
            "quality",
            "water_type",
            "distance_km",
            "location",
            "buyer_name",
            "buyer_phone",
            "status",
            "created_at"
        ])

# =========================================================
# HELPER FUNCTIONS
# =========================================================

def load_stps():
    with open(STP_FILE) as f:
        data = json.load(f)
        return data.get("stps", [])

def save_stps(stps):
    with open(STP_FILE, "w") as f:
        json.dump({"stps": stps}, f, indent=4)

def auto_reset_capacity():

    today = date.today().isoformat()
    stps = load_stps()
    updated = False

    for stp in stps:

        if "last_reset_date" not in stp:
            stp["last_reset_date"] = today

        if stp["last_reset_date"] != today:
            stp["available_capacity_mld"] = stp["total_capacity_mld"]
            stp["last_reset_date"] = today
            updated = True

    if updated:
        save_stps(stps)

def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat/2)**2 +
         math.cos(math.radians(lat1)) *
         math.cos(math.radians(lat2)) *
         math.sin(dlon/2)**2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

# =========================================================
# A* DISTANCE FUNCTION
# =========================================================
def astar_distance(lat1, lon1, lat2, lon2):
    
    if G is None:
        print("Using fallback distance")
        return haversine(lat1, lon1, lat2, lon2)

    try:
        start_node = ox.distance.nearest_nodes(G, lon1, lat1)
        end_node = ox.distance.nearest_nodes(G, lon2, lat2)

        distance_meters = nx.astar_path_length(G, start_node, end_node, weight="length")
        return distance_meters / 1000

    except Exception as e:
        print("A* failed, fallback:", e)
        return haversine(lat1, lon1, lat2, lon2)

    print("Running A* routing...")

    start_node = ox.distance.nearest_nodes(G, lon1, lat1)
    end_node = ox.distance.nearest_nodes(G, lon2, lat2)

    distance_meters = nx.astar_path_length(G, start_node, end_node, weight="length")

    distance_km = distance_meters / 1000

    print(f"A* distance: {distance_km:.2f} km")

    return distance_km

# =========================================================
# HOME + LOGIN
# =========================================================

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        role = request.form.get("role")
        if role == "stp":
            return redirect(url_for("supply"))
        elif role == "demand":
            session["buyer_name"] = request.form.get("name")
            session["buyer_phone"] = request.form.get("phone")
            return redirect(url_for("demand"))
        elif role == "tanker":
            return redirect(url_for("tanker_dashboard"))
        elif role == "admin":
            return redirect(url_for("admin_dashboard"))
    return render_template("login.html")


# =========================================================
# ADMIN DASHBOARD
# =========================================================

@app.route("/admin")
def admin_dashboard():
    stps = load_stps()

    orders = []
    if os.path.exists(ORDERS_FILE):
        with open(ORDERS_FILE, "r") as f:
            reader = csv.DictReader(f)
            orders = list(reader)

    return render_template("admin.html", stps=stps, orders=orders)


# =========================
# ADD STP
# =========================
@app.route("/admin/add_stp", methods=["POST"])
def add_stp():
    stps = load_stps()

    new_stp = {
        "stp_id": request.form["id"],
        "stp_name": request.form["name"],
        "latitude": float(request.form["lat"]),
        "longitude": float(request.form["lon"]),
        "technology": "Manual",
        "total_capacity_mld": float(request.form["capacity"]),
        "current_load_mld": 0.0,
        "available_capacity_mld": float(request.form["capacity"]),
        "treatment_cost_per_kl": 5.0,
        "quality_grade": "General",
        "last_reset_date": date.today().isoformat()
    }

    stps.append(new_stp)
    save_stps(stps)

    return redirect(url_for("admin_dashboard"))


# =========================
# DELETE STP
# =========================
@app.route("/admin/delete_stp/<stp_id>")
def delete_stp(stp_id):
    stps = load_stps()

    stps = [s for s in stps if str(s["stp_id"]) != str(stp_id)]

    save_stps(stps)

    return redirect(url_for("admin_dashboard"))

# =========================================================
# DEMAND SIDE
# =========================================================

@app.route('/demand')
def demand():
    return render_template("demand.html")

@app.route("/api/stps")
def api_stps():
    return jsonify(load_stps())

@app.route("/api/search_place")
def api_search_place():

    auto_reset_capacity()

    place = request.args.get("place")
    lat = request.args.get("lat")
    lon = request.args.get("lon")

    # 🔥 Decide input source
    if lat and lon:
        lat = float(lat)
        lon = float(lon)

        # 🔥 ADD THIS (reverse geocoding)
        reverse_url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}"
        try:
            response = requests.get(
                reverse_url,
                headers={"User-Agent": "wastewater-app"},
                timeout=5
            )
            data = response.json()
        except Exception as e:
            print("Reverse API failed:", e)
            data = {}

        address = data.get("address", {})

        # 🔥 STRONG ADDRESS BUILDER
        # ✅ CLEAN + CONSISTENT ADDRESS

        road = address.get("road")
        area = address.get("suburb") or address.get("neighbourhood")
        city = address.get("city") or address.get("town")
        state = address.get("state")
        pincode = address.get("postcode")

        location_name = ", ".join(filter(None, [
            road,
            city,
            state,
            pincode
        ]))

        # 🔥 GUARANTEED FALLBACK (NO "Live Location")
        if not location_name:
            location_name = f"{lat:.5f}, {lon:.5f}"

        if not location_name or location_name.strip() == "":
            location_name = f"{lat}, {lon}"

        print("Using LIVE coordinates:", lat, lon)

    elif place and place != "Using Live Location":
        geo_url = f"https://nominatim.openstreetmap.org/search?format=json&q={place}, Bangalore"
        response = requests.get(geo_url, headers={"User-Agent":"wastewater-app"})
        geo_data = response.json()

        if not geo_data:
            return jsonify({"error":"Place not found"}), 404

        lat = float(geo_data[0]["lat"])
        lon = float(geo_data[0]["lon"])
        location_name = place

    else:
        return jsonify({"error": "No location provided"}), 400

    # 🔥 ADD THIS BLOCK HERE (VERY IMPORTANT)

    required_kld_raw = request.args.get("required_kld")
    required_kld = float(required_kld_raw) if required_kld_raw and required_kld_raw.strip() != "" else 0

    required_quality = request.args.get("quality")
    required_type = request.args.get("type")

    stps = load_stps()
    nearby = []

    for stp in stps:

        if not stp.get("latitude") or not stp.get("longitude"):
            continue

        # FILTER BY QUALITY
        if required_quality and stp.get("quality_grade") != required_quality:
            continue
        
        # FILTER BY TYPE (SAFE FIX)
        if required_type and stp.get("water_type") and stp.get("water_type") != required_type:
            continue

        # Stage 1: Fast filtering
        approx_distance = haversine(lat, lon, stp["latitude"], stp["longitude"])

        if approx_distance > 100:
            continue

        # Stage 2: Accurate routing
        distance = astar_distance(lat, lon, stp["latitude"], stp["longitude"])

        if distance > 100:
            continue

        stp_copy = stp.copy()
        stp_copy["distance_km"] = round(distance,2)
        nearby.append(stp_copy)

    nearby.sort(key=lambda x: x["distance_km"])
    nearest = nearby[0] if nearby else None

    return jsonify({
        "searched_location":{
            "name":location_name,
            "latitude":lat,
            "longitude":lon
        },
        "nearest_stp":nearest
    })

@app.route("/create_order", methods=["POST"])
def create_order():

    data = request.json
    
    print("ORDER STP:", data["stp_id"]) 
     
    order_id = f"ORD{int(datetime.now().timestamp())}"

    row = {
        "order_id": order_id,
        "stp_id": data["stp_id"],
        "stp_name": data["stp_name"],
        "quantity_kld": data["quantity_kld"],
        "quality": data["quality"],
        "water_type": data["water_type"],
        "distance_km": data["distance_km"],
        "location": data["location"],
        "buyer_name": session.get("buyer_name") or "Unknown",
        "buyer_phone": session.get("buyer_phone") or "N/A",
        "status": "Pending",
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    with open(ORDERS_FILE, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "order_id","stp_id","stp_name","quantity_kld","quality",
            "water_type","distance_km","location",
            "buyer_name","buyer_phone","status","created_at"
        ])
        writer.writerow(row)

    return jsonify({"message":"Order created successfully"})

# =========================================================
# SUPPLY SIDE
# =========================================================

@app.route('/supply')
def supply():

    stps = load_stps()
    selected_id = request.args.get("stp_id")
    selected_stp = None
    prediction = None
    weekly_forecast = None

    if selected_id:
        for stp in stps:
            if str(stp["stp_id"]) == str(selected_id):
                selected_stp = stp

                try:
                    print("STP ID sent to ML:", stp["stp_id"])

                    prediction = predict_next_day(str(stp["stp_id"]))
                    weekly_forecast = predict_week(str(stp["stp_id"]))

                    if prediction is not None:
                        prediction = round(prediction, 2)

                    print("Prediction:", prediction)
                except Exception as e:
                    print("Prediction error:", e)
                    prediction = None

    demands = []

    if selected_stp and os.path.exists(ORDERS_FILE):
        with open(ORDERS_FILE, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                
                print("ROW STP:", row.get("stp_id"))
                print("SELECTED STP:", selected_stp["stp_id"])

                if row.get("stp_id", "").strip() == str(selected_stp["stp_id"]).strip():
                    
                    print("MATCHED:", row)

                    # ✅ SAFE CLEANING (handles None keys)
                    clean_row = {}

                    for k, v in row.items():
                        if k is None:
                            continue
                        clean_row[k.strip()] = v

                    row = clean_row
                    
                    print("ROW DATA:", row)
                    mapped_row = {
                        "request_id": row.get("order_id"),
                        "site_name": row.get("location"),
                        "quantity": row.get("quantity_kld"),
                        "quality_required": row.get("quality"),
                        "status": (row.get("status") or "").strip(),
                        "created_at": row.get("created_at")
                    }

                    demands.append(mapped_row)

    return render_template(
    "supply.html",
    stps=stps,
    selected_stp=selected_stp,
    demands=demands,
    prediction=prediction,
    weekly_forecast=weekly_forecast
    )

@app.route("/update_capacity", methods=["POST"])
def update_capacity():

    stp_id = request.form["stp_id"]
    new_capacity = float(request.form["available_capacity_mld"])

    stps = load_stps()

    for stp in stps:
        if str(stp["stp_id"]) == str(stp_id):
            stp["available_capacity_mld"] = new_capacity

    save_stps(stps)

    return redirect(url_for("supply", stp_id=stp_id))

@app.route("/upload_quality", methods=["POST"])
def upload_quality():

    stp_id = request.form["stp_id"]
    quality = request.form["quality_grade"]

    stps = load_stps()

    for stp in stps:
        if str(stp["stp_id"]) == str(stp_id):
            stp["quality_grade"] = quality

    save_stps(stps)

    return redirect(url_for("supply", stp_id=stp_id))

@app.route("/handle_request", methods=["POST"])
def handle_request():

    order_id = request.form["request_id"]
    action = request.form.get("action")

    updated_rows = []
    stp_id_redirect = None

    # ✅ STEP 1: READ FILE
    with open(ORDERS_FILE, "r") as f:
        reader = csv.DictReader(f)

        for row in reader:

            if row["order_id"].strip() == order_id.strip():

                stp_id_redirect = row["stp_id"]

                if action == "accept":
                    row["status"] = "Accepted"

                    # Deduct capacity
                    stps = load_stps()
                    for stp in stps:
                        if str(stp["stp_id"]) == row["stp_id"]:
                            quantity_mld = float(row["quantity_kld"]) / 1000
                            stp["available_capacity_mld"] -= quantity_mld
                    save_stps(stps)

                else:
                    row["status"] = "Rejected"

            updated_rows.append(row)

    # ✅ STEP 2: WRITE FILE (OUTSIDE ABOVE BLOCK)
    fieldnames = [
        "order_id",
        "stp_id",
        "stp_name",
        "quantity_kld",
        "quality",
        "water_type",
        "distance_km",
        "location",
        "buyer_name",
        "buyer_phone",
        "status",
        "created_at"
    ]

    with open(ORDERS_FILE, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(updated_rows)

    return redirect(url_for("supply", stp_id=stp_id_redirect))

@app.route("/tanker")
def tanker_dashboard():

    orders = []

    if os.path.exists(ORDERS_FILE):
        with open(ORDERS_FILE, "r") as f:
            reader = csv.DictReader(f)

            for row in reader:

                if row["status"] == "Accepted":

                    stps = load_stps()
                    stp_lat = None
                    stp_lon = None

                    for stp in stps:
                        if str(stp["stp_id"]) == str(row["stp_id"]):
                            stp_lat = stp.get("latitude")
                            stp_lon = stp.get("longitude")
                            break

                    row["stp_lat"] = stp_lat
                    row["stp_lon"] = stp_lon

                    orders.append(row)

    return render_template("tanker.html", orders=orders)

TANKER_CAPACITY_KLD = 12
AVAILABLE_TANKERS = 5

@app.route("/accept_pickup", methods=["POST"])
def accept_pickup():

    order_id = request.form.get("order_id")

    if not order_id:
        return "No Order ID received"

    updated_rows = []
    tanker_info = None
    stp_id_redirect = None

    with open(ORDERS_FILE, "r", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames

        for row in reader:

            # Strip spaces to avoid mismatch
            if row["order_id"].strip() == order_id.strip():
                stp_id_redirect = row["stp_id"]

                quantity = float(row["quantity_kld"])

                tankers_required = math.ceil(quantity / TANKER_CAPACITY_KLD)

                tanker_info = {
                    "order_id": row["order_id"],
                    "quantity": quantity,
                    "tankers_required": tankers_required,
                    "available_tankers": AVAILABLE_TANKERS,
                    "sufficient": tankers_required <= AVAILABLE_TANKERS,
                    "buyer_name": row.get("buyer_name"),
                    "buyer_phone": row.get("buyer_phone"),
                }

                row["status"] = "Out for Delivery"

            updated_rows.append(row)

    if tanker_info is None:
        return f"Order {order_id} not found in CSV"

    with open(ORDERS_FILE, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(updated_rows)
    
    
    return render_template(
    "tanker_summary.html",
    info=tanker_info,
    stp_id=stp_id_redirect
)

import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)