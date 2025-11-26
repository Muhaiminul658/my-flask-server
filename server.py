# ------------------- IMPORTS -------------------
from flask import Flask, request, jsonify
from flask_cors import CORS
import json, os, threading
import smtplib
from email.message import EmailMessage

# ------------------- FLASK APP -------------------
app = Flask(__name__)
CORS(app)
LOCK = threading.Lock()

# ------------------- FILE PATHS -------------------
USER_FILE = "users.json"
RECHARGE_FILE = "recharge_codes.json"

# ------------------- LOAD JSON -------------------
# Create missing files automatically
if not os.path.exists(USER_FILE):
    with open(USER_FILE, "w") as f:
        json.dump({}, f)

if not os.path.exists(RECHARGE_FILE):
    with open(RECHARGE_FILE, "w") as f:
        json.dump({}, f)

# ------------------- REGISTER -------------------
@app.route("/register", methods=["POST"])
def register():
    data = request.get_json() or {}
    username = data.get("username")
    password = data.get("password")
    email = data.get("email")

    if not username or not password or not email:
        return jsonify({"status": "error", "message": "Missing fields"})

    with LOCK:
        with open(USER_FILE, "r") as f:
            users = json.load(f)

        if username in users:
            return jsonify({"status": "error", "message": "Username already exists"})

        users[username] = {"password": password, "email": email, "coins": 0}

        with open(USER_FILE, "w") as f:
            json.dump(users, f, indent=4)

    return jsonify({"status": "success", "message": "Registered successfully"})


# ------------------- LOGIN -------------------
@app.route("/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    username = data.get("username")
    password = data.get("password")

    with open(USER_FILE, "r") as f:
        users = json.load(f)

    if username not in users:
        return jsonify({"status": "error", "message": "User not found"})

    if users[username]["password"] != password:
        return jsonify({"status": "error", "message": "Wrong password"})

    return jsonify({
        "status": "success",
        "message": "Login successful",
        "coins": users[username]["coins"]
    })


# ------------------- PROFILE -------------------
@app.route("/profile", methods=["POST"])
def profile():
    data = request.get_json() or {}
    username = data.get("username")

    with open(USER_FILE, "r") as f:
        users = json.load(f)

    if username not in users:
        return jsonify({"status": "error", "message": "User not found"})

    return jsonify({
        "status": "success",
        "username": username,
        "email": users[username]["email"],
        "coins": users[username]["coins"]
    })


# ------------------- RECHARGE (User uses a code) -------------------
@app.route("/recharge", methods=["POST"])
def recharge():
    data = request.get_json() or {}
    username = data.get("username")
    code = data.get("code")

    with LOCK:
        with open(USER_FILE, "r") as f:
            users = json.load(f)
        with open(RECHARGE_FILE, "r") as f:
            recharge_data = json.load(f)

        if code not in recharge_data:
            return jsonify({"status": "error", "message": "Invalid code"})

        coins_to_add = recharge_data[code]
        users[username]["coins"] += coins_to_add

        # Delete used code
        del recharge_data[code]

        with open(USER_FILE, "w") as f:
            json.dump(users, f, indent=4)
        with open(RECHARGE_FILE, "w") as f:
            json.dump(recharge_data, f, indent=4)

    return jsonify({"status": "success", "coins": users[username]["coins"]})


# ------------------- ADMIN: ADD RECHARGE CODE -------------------
@app.route("/admin_add_recharge", methods=["POST"])
def admin_add_recharge():
    data = request.get_json() or {}
    code = data.get("code")
    coins = data.get("coins")

    if not code or not coins:
        return jsonify({"status": "error", "message": "Missing code or coins"})

    with LOCK:
        with open(RECHARGE_FILE, "r") as f:
            recharge_data = json.load(f)

        recharge_data[code] = coins

        with open(RECHARGE_FILE, "w") as f:
            json.dump(recharge_data, f, indent=4)

    return jsonify({"status": "success", "message": "Recharge code added"})


# ------------------- RUN SERVER -------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
