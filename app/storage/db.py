import mysql.connector
from flask import g, current_app

from app.storage import mapper


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


def get_db_conf():
    return current_app.config.get('DATABASE')


def get_hosts() -> [str]:
    return get_entity_simple("host")


def get_services() -> [str]:
    return get_entity_simple("service")


def get_entity_simple(entity) -> [str]:
    database = get_db(cfg=get_db_conf())
    db_cursor = database.cursor()
    db_cursor.execute(f"SELECT DISTINCT {entity} FROM {get_db_conf()['status_table']}")
    entities = []
    for r in db_cursor.fetchall():
        entities.append(r[0])
    db_cursor.close()
    database.commit()
    return entities


def get_event_with_earliest_before_status(host, service, date):
    database = get_db(cfg=get_db_conf())
    db_cursor = database.cursor()
    db_cursor.execute(
        f"SELECT timestamp('{date}'), status, host"
        f" FROM {get_db_conf()['status_table']}"
        f" WHERE event_time < '{date}'"
        f" AND service = '{service}'"
        f" AND host = '{host}'"
        f" ORDER BY event_time DESC LIMIT 1"
    )
    first_status = db_cursor.fetchone()
    db_cursor.close()
    database.commit()
    if first_status:
        return mapper.map_event(first_status)
    return None


def get_events_between(host, service, start_date, end_date):
    database = get_db(cfg=get_db_conf())
    sql = (
        f"SELECT event_time, status, host"
        f" FROM {get_db_conf()['status_table']}"
        f" WHERE event_time BETWEEN '{start_date}' AND '{end_date}'"
        f" AND service = '{service}'"
    )
    if host:
        sql += f" AND host = '{host}'"
    sql += f" ORDER BY event_time ASC"

    db_cursor = database.cursor()
    db_cursor.execute(sql)
    data = db_cursor.fetchall()
    db_cursor.close()
    database.commit()
    return mapper.map_events(data)


def insert_event(host, status, monitored_service):
    database = get_db(cfg=get_db_conf())
    db_cursor = database.cursor()
    db_cursor.execute(f"""
            INSERT INTO {get_db_conf()['status_table']}(host, status, service, event_time)
            VALUES (%(host)s, %(status)s, %(service)s, NOW())
        """, {
        'host': host,
        'status': status,
        'service': monitored_service
    })
    db_cursor.close()
    database.commit()
