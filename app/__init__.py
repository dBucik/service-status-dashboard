from flask import Flask

from app import config
from app.storage import db
from werkzeug.security import generate_password_hash

def create_app():
    app = Flask(__name__)
    conf = config.load_config()
    app.config["DATABASE"] = conf["database"]
    app.config["SERVICES"] = conf["services"]

    user_dict = conf["security"]
    users = {}
    for user, passw in user_dict.items():
        users[user] = generate_password_hash(passw)
    app.config["WEB_SECURITY_USERS"] = users

    db.init_app(app)

    from app.handlers import bp as handlers_bp
    app.register_blueprint(handlers_bp)

    return app
