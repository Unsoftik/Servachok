from flask import Flask, request, jsonify
import json
import os

app = Flask(__name__)

USER_DB_FILE = 'users.json'

def load_users():
    if os.path.exists(USER_DB_FILE):
        with open(USER_DB_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_users(users):
    with open(USER_DB_FILE, 'w') as f:
        json.dump(users, f)

@app.route("/register", methods=["POST"])
def register():
    username = request.form.get("username")
    password = request.form.get("password")
    pin_code = request.form.get("pin")

    users = load_users()

    if username in users:
        return jsonify({"message": "Пользователь уже существует!"}), 400

    if not password:
        return jsonify({"message": "Пароль не может быть пустым!"}), 400

    users[username] = {'password': password}
    save_users(users)
    return jsonify({"message": "Регистрация успешна!"}), 200

@app.route("/login", methods=["POST"])
def login():
    username = request.form.get("username")
    password = request.form.get("password")

    users = load_users()

    if username not in users or users[username]['password'] != password:
        return jsonify({"message": "Неверный логин или пароль."}), 400

    return jsonify({"message": "Вход успешен!"}), 200

@app.route("/get_users", methods=["GET"])
def get_users():
    users = load_users()
    
    # Возвращаем пользователей с паролями
    return jsonify(users)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8080)
