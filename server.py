## ------------------- IMPORTS -------------------
from flask import Flask, request, jsonify
from flask_cors import CORS
import json, os, threading
import smtplib
from email.message import EmailMessage
from pyngrok import ngrok
from email_config import EMAIL_USER, EMAIL_PASS

# ------------------- FLASK APP -------------------
app = Flask(__name__)
CORS(app)  # 🔹 Enable CORS for all routes
LOCK = threading.Lock()

# ------------------- NGROK AUTH -------------------
NGROK_AUTH = "35vCSYErL5OfFG7seyGR7lW2PTt_7Va1gycMX3FD7ssukFpqB"
ngrok.set_auth_token(NGROK_AUTH)
public_url = ngrok.connect(5000)
print("SERVER URL:", public_url)

# ------------------- FILE PATHS -------------------
USER_FILE = "users.json"
PRODUCT_FILE = "products.json"
RECHARGE_FILE = "recharge.json"
ORDER_FILE = "orders.json"

# ------------------- HELPERS -------------------
def ensure_file(path, default):
    if not os.path.exists(path):
        with open(path, "w") as f:
            json.dump(default, f, indent=2)

def load(path):
    ensure_file(path, {})
    with open(path, "r") as f:
        try:
            return json.load(f)
        except:
            return {}

def save(path, data):
    with LOCK:
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

# ---------------- EMAIL SYSTEM -------------------
ADMIN_EMAIL = EMAIL_USER

def _send_email(subject, body, to=ADMIN_EMAIL):
    msg = EmailMessage()
    msg["From"] = EMAIL_USER
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(EMAIL_USER, EMAIL_PASS)
            smtp.send_message(msg)
        print("Email sent:", subject)
    except Exception as e:
        print("Email error:", e)

def send_email_async(subject, body, to=ADMIN_EMAIL):
    threading.Thread(target=_send_email, args=(subject, body, to), daemon=True).start()

# ------------------- REGISTER -------------------
@app.route("/register", methods=["POST"])
def register():
    data = request.get_json() or {}
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"status": "error", "msg": "username/password required"}), 400

    users = load(USER_FILE)
    if username in users:
        return jsonify({"status": "error", "msg": "username exists"}), 400

    users[username] = {"password": password, "coins": 0, "orders": []}
    save(USER_FILE, users)

    return jsonify({"status": "success", "coins": 0})

# ------------------- LOGIN -------------------
@app.route("/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    username = data.get("username")
    password = data.get("password")

    users = load(USER_FILE)
    if username in users and users[username]["password"] == password:
        return jsonify({"status": "success", "coins": users[username]["coins"]})

    return jsonify({"status": "error", "msg": "invalid credentials"}), 401

# ------------------- PRODUCTS -------------------
@app.route("/products", methods=["GET"])
def get_products():
    return jsonify(load(PRODUCT_FILE))

@app.route("/admin_add_product", methods=["POST"])
def admin_add_product():
    data = request.get_json() or {}
    name = data.get("name")
    price = data.get("price")

    if not name or price is None:
        return jsonify({"status": "error", "msg": "name & price required"}), 400

    products = load(PRODUCT_FILE)
    pid = str(max([int(k) for k in products.keys()] + [0]) + 1)

    products[pid] = {"name": name, "price": int(price)}
    save(PRODUCT_FILE, products)

    return jsonify({"status": "success", "id": pid})

@app.route("/admin_delete_product", methods=["POST"])
def admin_delete_product():
    data = request.get_json() or {}
    pid = str(data.get("id"))

    products = load(PRODUCT_FILE)
    if pid in products:
        del products[pid]
        save(PRODUCT_FILE, products)
        return jsonify({"status": "success"})

    return jsonify({"status": "error", "msg": "not_found"}), 404

# ------------------- RECHARGE -------------------
@app.route("/recharge", methods=["POST"])
def recharge():
    data = request.get_json() or {}
    username = data.get("username")
    code = str(data.get("code"))

    users = load(USER_FILE)
    codes = load(RECHARGE_FILE)

    if username not in users:
        return jsonify({"status": "error", "msg": "user_not_found"}), 404

    if code not in codes:
        return jsonify({"status": "error", "msg": "invalid_code"}), 404

    if codes[code]["used"]:
        return jsonify({"status": "error", "msg": "already_used"}), 400

    amount = codes[code]["amount"]
    users[username]["coins"] += amount
    codes[code]["used"] = True

    save(USER_FILE, users)
    save(RECHARGE_FILE, codes)

    return jsonify({"status": "success", "coins": users[username]["coins"]})

@app.route("/admin_add_recharge", methods=["POST"])
def admin_add_recharge():
    data = request.get_json() or {}
    code = str(data.get("code"))
    amount = data.get("amount")

    if not code or amount is None:
        return jsonify({"status": "error", "msg": "code & amount required"}), 400

    codes = load(RECHARGE_FILE)
    codes[code] = {"amount": int(amount), "used": False}

    save(RECHARGE_FILE, codes)
    return jsonify({"status": "success"})

@app.route("/admin_delete_recharge", methods=["POST"])
def admin_delete_recharge():
    data = request.get_json() or {}
    code = str(data.get("code"))

    codes = load(RECHARGE_FILE)
    if code in codes:
        del codes[code]
        save(RECHARGE_FILE, codes)
        return jsonify({"status": "success"})

    return jsonify({"status": "error", "msg": "not_found"}), 404

# ------------------- BUY PRODUCT -------------------
@app.route("/buy_product", methods=["POST"])
def buy_product():
    data = request.get_json() or {}
    username = data.get("username")
    pid = str(data.get("product_id"))
    courier = bool(data.get("courier", False))
    address = data.get("address", "")
    phone = data.get("phone", "")

    users = load(USER_FILE)
    products = load(PRODUCT_FILE)
    orders = load(ORDER_FILE)

    if username not in users:
        return jsonify({"status": "error", "msg": "user_not_found"}), 404

    if pid not in products:
        return jsonify({"status": "error", "msg": "product_not_found"}), 404

    price = products[pid]["price"]
    if users[username]["coins"] < price:
        return jsonify({"status": "error", "msg": "not_enough_coins"}), 400

    users[username]["coins"] -= price

    oid = str(max([int(k) for k in orders.keys()] + [0]) + 1)
    orders[oid] = {
        "user": username,
        "product": pid,
        "courier": courier,
        "address": address,
        "phone": phone,
        "status": "pending"
    }

    save(USER_FILE, users)
    save(ORDER_FILE, orders)

    send_email_async(
        "New Order Received",
        f"User: {username}\nProduct ID: {pid}\nAddress: {address}\nPhone: {phone}"
    )

    return jsonify({"status": "success", "order_id": oid, "coins": users[username]["coins"]})

# ------------------- RUN SERVER -------------------
if __name__ == "__main__":
    app.run(port=5000)
