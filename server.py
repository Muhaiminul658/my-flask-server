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


# ------------------- RECHARGE (Apply Code) -------------------
@app.route("/recharge", methods=["POST"])
def recharge():
    data = request.get_json() or {}
    username = data.get("username")
    code = data.get("code")

    with open(USER_FILE, "r") as f:
        users = json.load(f)

    with open(RECHARGE_FILE, "r") as f:
        codes = json.load(f)

    if username not in users:
        return jsonify({"status": "error", "message": "User not found"})

    if code not in codes:
        return jsonify({"status": "error", "message": "Invalid code"})

    coin_amount = codes[code]

    # Update coins
    users[username]["coins"] += coin_amount

    # Delete used code
    del codes[code]

    with LOCK:
        with open(USER_FILE, "w") as f:
            json.dump(users, f, indent=4)
        with open(RECHARGE_FILE, "w") as f:
            json.dump(codes, f, indent=4)

    return jsonify({
        "status": "success",
        "message": "Recharge successful",
        "coins": users[username]["coins"]
    })


# ------------------- ADMIN: Add Recharge Code -------------------
@app.route("/admin_add_code", methods=["POST"])
def admin_add_code():
    data = request.get_json() or {}
    code = data.get("code")
    coins = data.get("coins")

    if not code or not coins:
        return jsonify({"status": "error", "message": "Missing fields"})

    with open(RECHARGE_FILE, "r") as f:
        codes = json.load(f)

    codes[code] = coins

    with LOCK:
        with open(RECHARGE_FILE, "w") as f:
            json.dump(codes, f, indent=4)

    return jsonify({"status": "success", "message": "Code added"})


# ------------------- RUN SERVER -------------------
if __name__ == "__main__":
    app.run(port=5000, debug=True)
