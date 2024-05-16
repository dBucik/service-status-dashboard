import mysql.connector
from flask import g


def close_db(e=None):
    db = g.pop('db', None)

    if db is not None and db.is_connected():
        db.close()


def init_app(app):
    app.teardown_appcontext(close_db)


def get_db(cfg):
    if 'db' not in g or not g.db.is_connected():
        g.db = mysql.connector.connect(
            host=cfg["host"],
            user=cfg["user"],
            password=cfg["password"],
            database=cfg["database"],
        )
    return g.db

