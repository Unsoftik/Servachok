from flask import Flask, request, jsonify
import json
import os
try:
 from flask_cors import CORS
except ModuleNotFoundError:
    os.system('pip install flask_cors')
    from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Добавляем поддержку CORS

USER_DB_FILE = 'users.json'
PROTOCOL_STATE_FILE = 'protocol.json'

def load_users():
    if os.path.exists(USER_DB_FILE):
        with open(USER_DB_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_users(users):
    with open(USER_DB_FILE, 'w') as f:
        json.dump(users, f, indent=4)  # Добавлен indent для читаемости JSON

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
    
    # Получаем данные из запроса
    username = request.form.get("username")
    password = request.form.get("password")
    pin_code = request.form.get("pin")
    developer = request.form.get("developer", "0")  # По умолчанию обычный пользователь
    friend = request.form.get("friend", "0")        # По умолчанию не друг

    # Отладочный вывод для проверки входных данных
    print(f"Регистрация: username={username}, password={password}, pin={pin_code}, developer={developer}, friend={friend}")

    users = load_users()

    # Проверка пин-кода
    if not check_pin(pin_code):
        return jsonify({"message": "Неверный пин-код!"}), 400

    # Проверка существования пользователя
    if username in users:
        return jsonify({"message": "Пользователь уже существует!"}), 400

    # Проверка пароля
    if not password:
        return jsonify({"message": "Пароль не может быть пустым!"}), 400

    # Сохранение пользователя с явной логикой ролей
    users[username] = {
        'password': password,
        'developer': developer == "1",  # True если "1", иначе False
        'friend': friend == "2"         # True если "2", иначе False
    }
    
    save_users(users)
    print(f"Сохранено: {users[username]}")  # Отладка сохраненных данных
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

    return jsonify({"message": "Вход успешен!"}), 200

@app.route("/get_users", methods=["GET"])
def get_users():
    if load_protocol_state():
        return jsonify({"message": "Zero protocol activated"}), 403
    users = load_users()
    return jsonify(users)

@app.route("/delete_user", methods=["POST"])
def delete_user():
    if load_protocol_state():
        return jsonify({"message": "Нулевой протокол активирован. Действие невозможно."}), 403
    
    username = request.form.get("username")
    pin_code = request.form.get("pin")
    
    print(f"Попытка удалить: username={username}, pin={pin_code}")  # Отладка
    
    if not check_pin(pin_code):
        return jsonify({"message": "Неверный пин-код!"}), 400
    
    users = load_users()
    
    if username not in users:
        return jsonify({"message": "Пользователь не найден!"}), 404
    
    del users[username]
    save_users(users)
    return jsonify({"message": f"Пользователь {username} успешно удален!"}), 200

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8080)
