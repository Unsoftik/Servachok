from flask import Flask, request, jsonify
import json
import os
from datetime import datetime

try:
    from flask_cors import CORS
except ModuleNotFoundError:
    os.system('pip install flask_cors')
    from flask_cors import CORS

app = Flask(__name__)
CORS(app)

USER_DB_FILE = 'users.json'
PROTOCOL_STATE_FILE = 'protocol.json'

def load_users():
    if os.path.exists(USER_DB_FILE):
        with open(USER_DB_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_users(users):
    with open(USER_DB_FILE, 'w') as f:
        json.dump(users, f, indent=4)

def load_protocol_state():
    if os.path.exists(PROTOCOL_STATE_FILE):
        with open(PROTOCOL_STATE_FILE, 'r') as f:
            return json.load(f).get('zero_protocol', False)
    return False

def save_protocol_state(state):
    with open(PROTOCOL_STATE_FILE, 'w') as f:
        json.dump({'zero_protocol': state}, f, indent=4)

def check_pin(pin_code):
    correct_pin = "1312"
    return pin_code == correct_pin

def check_registration_pin(pin_code):
    correct_reg_pin = "2023"  # Отдельный пин-код для регистрации
    return pin_code == correct_reg_pin

@app.route("/activate_zero_protocol", methods=["POST"])
def activate_zero_protocol():
    pin_code = request.form.get("pin")
    if not check_pin(pin_code):
        return jsonify({"message": "Неверный пин-код!"}), 400
    save_protocol_state(True)
    return jsonify({"message": "Нулевой протокол активирован!"}), 200

@app.route("/deactivate_zero_protocol", methods=["POST"])
def deactivate_zero_protocol():
    pin_code = request.form.get("pin")
    if not check_pin(pin_code):
        return jsonify({"message": "Неверный пин-код!"}), 400
    save_protocol_state(False)
    return jsonify({"message": "Нулевой протокол деактивирован!"}), 200

@app.route("/register", methods=["POST"])
def register():
    if load_protocol_state():
        return jsonify({"message": "Нулевой протокол активирован. Действие невозможно."}), 403
    
    username = request.form.get("username")
    password = request.form.get("password")
    pin_code = request.form.get("pin")
    developer = request.form.get("developer", "0")
    friend = request.form.get("friend", "0")

    print(f"Регистрация: username={username}, password={password}, pin={pin_code}, developer={developer}, friend={friend}")

    users = load_users()

    if not check_registration_pin(pin_code):
        return jsonify({"message": "Неверный пин-код для регистрации!"}), 400

    if username in users:
        return jsonify({"message": "Пользователь уже существует!"}), 400

    if not password:
        return jsonify({"message": "Пароль не может быть пустым!"}), 400

    registration_date = datetime.now().strftime("%B %Y")

    users[username] = {
        'password': password,
        'developer': developer == "1",
        'friend': friend == "2",
        'banned': False,
        'registration_date': registration_date
    }
    
    save_users(users)
    print(f"Сохранено: {users[username]}")
    return jsonify({"message": "Регистрация успешна!"}), 200

@app.route("/login", methods=["POST"])
def login():
    if load_protocol_state():
        return jsonify({"message": "Zero protocol activated"}), 403
    
    username = request.form.get("username")
    password = request.form.get("password")

    users = load_users()

    if username not in users or users[username]['password'] != password:
        return jsonify({"message": "Неверный логин или пароль."}), 400
    
    if users[username]['banned']:
        return jsonify({"message": "Пользователь забанен!"}), 406

    return jsonify({"message": "Вход успешен!"}), 200

@app.route("/check_registration", methods=["GET"])
def check_registration():
    if load_protocol_state():
        return jsonify({"message": "Нулевой протокол активирован. Действие невозможно."}), 403
    
    username = request.args.get("username")
    users = load_users()
    
    if username in users:
        return jsonify({
            "registration_date": users[username]['registration_date']
        }), 200
    return jsonify({
        "registration_date": None
    }), 200

@app.route("/check_ban_status", methods=["GET"])
def check_ban_status():
    if load_protocol_state():
        return jsonify({"message": "Нулевой протокол активирован. Действие невозможно."}), 403
    
    username = request.args.get("username")
    users = load_users()
    
    if username not in users:
        return jsonify({
            "message": "Пользователь не найден",
            "exists": False
        }), 404
    
    return jsonify({
        "message": "Статус пользователя получен",
        "exists": True,
        "banned": users[username]['banned']
    }), 200

@app.route("/get_users", methods=["GET"])
def get_users():
    if load_protocol_state():
        return jsonify({"message": "Zero protocol activated"}), 403
    
    pin_code = request.args.get("pin")
    if not check_pin(pin_code):
        return jsonify({"message": "Неверный пин-код!"}), 400
        
    users = load_users()
    return jsonify(users)

@app.route("/delete_user", methods=["POST"])
def delete_user():
    if load_protocol_state():
        return jsonify({"message": "Нулевой протокол активирован. Действие невозможно."}), 403
    
    username = request.form.get("username")
    pin_code = request.form.get("pin")
    
    if not check_pin(pin_code):
        return jsonify({"message": "Неверный пин-код!"}), 400
    
    users = load_users()
    
    if username not in users:
        return jsonify({"message": "Пользователь не найден!"}), 404
    
    del users[username]
    save_users(users)
    return jsonify({"message": f"Пользователь {username} успешно удален!"}), 200

@app.route("/ban_user", methods=["POST"])
def ban_user():
    if load_protocol_state():
        return jsonify({"message": "Нулевой протокол активирован. Действие невозможно."}), 403
    
    username = request.form.get("username")
    pin_code = request.form.get("pin")
    
    if not check_pin(pin_code):
        return jsonify({"message": "Неверный пин-код!"}), 400
    
    users = load_users()
    
    if username not in users:
        return jsonify({"message": "Пользователь не найден!"}), 404
    
    users[username]['banned'] = True
    save_users(users)
    return jsonify({"message": f"Пользователь {username} успешно забанен!"}), 200

@app.route("/unban_user", methods=["POST"])
def unban_user():
    if load_protocol_state():
        return jsonify({"message": "Нулевой протокол активирован. Действие невозможно."}), 403
    
    username = request.form.get("username")
    pin_code = request.form.get("pin")
    
    if not check_pin(pin_code):
        return jsonify({"message": "Неверный пин-код!"}), 400
    
    users = load_users()
    
    if username not in users:
        return jsonify({"message": "Пользователь не найден!"}), 404
    
    users[username]['banned'] = False
    save_users(users)
    return jsonify({"message": f"Пользователь {username} успешно разбанен!"}), 200

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8080)
