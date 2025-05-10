from flask import Flask, request, jsonify
import os
from datetime import datetime, timedelta
import bcrypt
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import uuid

try:
    from flask_cors import CORS
except ModuleNotFoundError:
    os.system('pip install flask_cors')
    from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Настройка базы данных
database_url = os.getenv('DATABASE_URL')
if not database_url:
    raise ValueError("DATABASE_URL is not set in environment variables")
if database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Модель для пользователей
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    developer = db.Column(db.Boolean, default=False)
    friend = db.Column(db.Boolean, default=False)
    banned = db.Column(db.Boolean, default=False)
    registration_date = db.Column(db.String(20), nullable=False)
    key_id = db.Column(db.Integer, db.ForeignKey('keys.id'), nullable=True)

# Модель для ключей
class Key(db.Model):
    __tablename__ = 'keys'
    id = db.Column(db.Integer, primary_key=True)
    key_value = db.Column(db.String(36), unique=True, nullable=False)  # UUID для ключа
    duration_days = db.Column(db.Integer, nullable=False)  # 15, 30 или -1 (навсегда)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=True)
    used = db.Column(db.Boolean, default=False)

# Модель для состояния протокола, версии программы и ссылки на обновление
class SystemState(db.Model):
    __tablename__ = 'system_state'
    id = db.Column(db.Integer, primary_key=True)
    zero_protocol = db.Column(db.Boolean, default=False)
    program_version = db.Column(db.String(20), default='1.0.0')
    update_url = db.Column(db.String(255), nullable=True)

# Проверка пин-кодов
def check_admin_pin(pin_code):
    return pin_code == "1312"

def check_users_pin(pin_code):
    return pin_code == "2024"

# Инициализация базы данных
with app.app_context():
    db.create_all()
    if not SystemState.query.first():
        db.session.add(SystemState(zero_protocol=False, program_version='1.0.0', update_url=None))
        db.session.commit()

# Проверка и удаление истекших аккаунтов
def check_expired_keys():
    keys = Key.query.filter(Key.used == True, Key.expires_at != None).all()
    current_time = datetime.utcnow()
    for key in keys:
        if key.expires_at < current_time:
            user = User.query.filter_by(key_id=key.id).first()
            if user:
                db.session.delete(user)
            key.used = False  # Ключ становится неиспользованным
            db.session.commit()

@app.route("/activate_zero_protocol", methods=["POST"])
def activate_zero_protocol():
    pin_code = request.form.get("pin")
    if not check_admin_pin(pin_code):
        return jsonify({"message": "Неверный пин-код!"}), 400
    state = SystemState.query.first()
    state.zero_protocol = True
    db.session.commit()
    return jsonify({"message": "Нулевой протокол активирован!"}), 200

@app.route("/deactivate_zero_protocol", methods=["POST"])
def deactivate_zero_protocol():
    pin_code = request.form.get("pin")
    if not check_admin_pin(pin_code):
        return jsonify({"message": "Неверный пин-код!"}), 400
    state = SystemState.query.first()
    state.zero_protocol = False
    db.session.commit()
    return jsonify({"message": "Нулевой протокол деактивирован!"}), 200

@app.route("/delete_all_users", methods=["POST"])
def delete_all_users():
    state = SystemState.query.first()
    if state.zero_protocol:
        return jsonify({"message": "Нулевой протокол активирован. Действие невозможно."}), 403
    
    pin_code = request.form.get("pin")
    if not check_admin_pin(pin_code):
        return jsonify({"message": "Неверный пин-код!"}), 400
    
    User.query.delete()
    Key.query.delete()  # Удаляем также все ключи
    db.session.commit()
    
    return jsonify({"message": "Все пользователи и ключи успешно удалены!"}), 200

@app.route("/create_key", methods=["POST"])
def create_key():
    pin_code = request.form.get("pin")
    duration = request.form.get("duration")  # 15, 30 или -1 (навсегда)
    
    if not check_admin_pin(pin_code):
        return jsonify({"message": "Неверный пин-код!"}), 400
    
    if duration not in ["15", "30", "-1"]:
        return jsonify({"message": "Недопустимая длительность ключа! Используйте 15, 30 или -1."}), 400
    
    duration = int(duration)
    key_value = str(uuid.uuid4())  # Генерируем уникальный ключ
    expires_at = None
    if duration != -1:
        expires_at = datetime.utcnow() + timedelta(days=duration)
    
    new_key = Key(
        key_value=key_value,
        duration_days=duration,
        expires_at=expires_at,
        used=False
    )
    db.session.add(new_key)
    db.session.commit()
    
    return jsonify({"message": "Ключ успешно создан!", "key": key_value}), 200

@app.route("/register", methods=["POST"])
def register():
    state = SystemState.query.first()
    if state.zero_protocol:
        return jsonify({"message": "Нулевой протокол активирован. Действие невозможно."}), 403
    
    username = request.form.get("username")
    password = request.form.get("password")
    key_value = request.form.get("key")
    developer = request.form.get("developer", "0")
    friend = request.form.get("friend", "0")

    # Проверяем ключ
    key = Key.query.filter_by(key_value=key_value).first()
    if not key:
        return jsonify({"message": "Неверный ключ!"}), 400
    if key.used:
        return jsonify({"message": "Ключ уже использован!"}), 400
    if key.expires_at and key.expires_at < datetime.utcnow():
        return jsonify({"message": "Срок действия ключа истек!"}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({"message": "Пользователь уже существует!"}), 400

    if not password:
        return jsonify({"message": "Пароль не может быть пустым!"}), 400

    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    registration_date = datetime.now().strftime("%B %Y")

    new_user = User(
        username=username,
        password=hashed_password.decode('utf-8'),
        developer=developer == "1",
        friend=friend == "2",
        banned=False,
        registration_date=registration_date,
        key_id=key.id
    )
    key.used = True
    db.session.add(new_user)
    db.session.commit()
    
    # Проверяем истекшие ключи после регистрации
    check_expired_keys()
    
    return jsonify({"message": "Регистрация успешна!"}), 200

@app.route("/login", methods=["POST"])
def login():
    state = SystemState.query.first()
    if state.zero_protocol:
        return jsonify({"message": "Zero protocol activated"}), 403
    
    username = request.form.get("username")
    password = request.form.get("password")

    user = User.query.filter_by(username=username).first()
    if not user or not bcrypt.checkpw(password.encode('utf-8'), user.password.encode('utf-8')):
        return jsonify({"message": "Неверный логин или пароль."}), 400
    
    if user.banned:
        return jsonify({"message": "Пользователь забанен!"}), 406

    # Проверяем истекшие ключи при входе
    check_expired_keys()
    
    if not User.query.filter_by(username=username).first():
        return jsonify({"message": "Аккаунт удален из-за истечения срока действия ключа."}), 403
    
    return jsonify({"message": "Вход успешен!"}), 200

@app.route("/get_version", methods=["GET"])
def get_version():
    state = SystemState.query.first()
    return jsonify({"version": state.program_version}), 200

@app.route("/update_version", methods=["POST"])
def update_version():
    pin_code = request.form.get("pin")
    new_version = request.form.get("version")
    update_url = request.form.get("update_url")
    if not check_admin_pin(pin_code):
        return jsonify({"message": "Неверный пин-код!"}), 400
    if not new_version:
        return jsonify({"message": "Новая версия не указана!"}), 400
    state = SystemState.query.first()
    state.program_version = new_version
    state.update_url = update_url
    db.session.commit()
    return jsonify({"message": f"Версия обновлена до {new_version}!"}), 200

@app.route("/get_update", methods=["GET"])
def get_update():
    state = SystemState.query.first()
    if not state.update_url:
        return jsonify({"message": "Ссылка на обновление не установлена."}), 404
    return jsonify({"update_url": state.update_url}), 200

@app.route("/check_registration", methods=["GET"])
def check_registration():
    state = SystemState.query.first()
    if state.zero_protocol:
        return jsonify({"message": "Нулевой протокол активирован. Действие невозможно."}), 403
    
    username = request.args.get("username")
    user = User.query.filter_by(username=username).first()
    return jsonify({
        "registration_date": user.registration_date if user else None
    }), 200

@app.route("/check_ban_status", methods=["GET"])
def check_ban_status():
    state = SystemState.query.first()
    if state.zero_protocol:
        return jsonify({"message": "Нулевой протокол активирован. Действие невозможно."}), 403
    
    username = request.args.get("username")
    user = User.query.filter_by(username=username).first()
    
    if not user:
        return jsonify({"message": "Пользователь не найден", "exists": False}), 404
    
    return jsonify({"message": "Статус пользователя получен", "exists": True, "banned": user.banned}), 200

@app.route("/get_users", methods=["GET"])
def get_users():
    state = SystemState.query.first()
    if state.zero_protocol:
        return jsonify({"message": "Zero protocol activated"}), 403
    
    pin_code = request.args.get("pin")
    if not check_users_pin(pin_code):
        return jsonify({"message": "Неверный пин-код для получения списка пользователей!"}), 400
        
    users = User.query.all()
    return jsonify({user.username: {
        "password": user.password,
        "developer": user.developer,
        "friend": user.friend,
        "banned": user.banned,
        "registration_date": user.registration_date
    } for user in users})

@app.route("/delete_user", methods=["POST"])
def delete_user():
    state = SystemState.query.first()
    if state.zero_protocol:
        return jsonify({"message": "Нулевой протокол активирован. Действие невозможно."}), 403
    
    username = request.form.get("username")
    pin_code = request.form.get("pin")
    
    if not check_admin_pin(pin_code):
        return jsonify({"message": "Неверный пин-код!"}), 400
    
    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify({"message": "Пользователь не найден!"}), 404
    
    key = Key.query.get(user.key_id)
    if key:
        key.used = False
    db.session.delete(user)
    db.session.commit()
    return jsonify({"message": f"Пользователь {username} успешно удален!"}), 200

@app.route("/ban_user", methods=["POST"])
def ban_user():
    state = SystemState.query.first()
    if state.zero_protocol:
        return jsonify({"message": "Нулевой протокол активирован. Действие невозможно."}), 403
    
    username = request.form.get("username")
    pin_code = request.form.get("pin")
    
    if not check_admin_pin(pin_code):
        return jsonify({"message": "Неверный пин-код!"}), 400
    
    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify({"message": "Пользователь не найден!"}), 404
    
    user.banned = True
    db.session.commit()
    return jsonify({"message": f"Пользователь {username} успешно забанен!"}), 200

@app.route("/unban_user", methods=["POST"])
def unban_user():
    state = SystemState.query.first()
    if state.zero_protocol:
        return jsonify({"message": "Нулевой протокол активирован. Действие невозможно."}), 403
    
    username = request.form.get("username")
    pin_code = request.form.get("pin")
    
    if not check_admin_pin(pin_code):
        return jsonify({"message": "Неверный пин-код!"}), 400
    
    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify({"message": "Пользователь не найден!"}), 404
    
    user.banned = False
    db.session.commit()
    return jsonify({"message": f"Пользователь {username} успешно разбанен!"}), 200

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8080)
