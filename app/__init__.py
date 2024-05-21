from flask import Flask

from app import config
from app.storage import db


def create_app():
    app = Flask(__name__)
    conf = config.load_config()
    app.config["DATABASE"] = conf["database"]
    app.config["SERVICES"] = conf["services"]

    db.init_app(app)

    from app.handlers import bp as handlers_bp
    app.register_blueprint(handlers_bp)

    return app
