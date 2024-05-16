from flask import current_app, g

import mysql.connector


def get_db(cfg):
    if 'db' not in g or not g.db.is_connected():
        g.db = mysql.connector.connect(
            host=cfg["database"]["host"],
            user=cfg["database"]["user"],
            password=cfg["database"]["password"],
            database=cfg["database"]["database"],
        )
    return g.db


def close_db(e=None):
    db = g.pop('db', None)

    if db is not None and db.is_connected():
        db.close()


current_app.teardown_appcontext(close_db)