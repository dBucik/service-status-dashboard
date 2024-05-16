from datetime import datetime, timedelta

from dateutil.relativedelta import relativedelta
from flask import redirect, url_for, request, render_template, current_app

from app import db
from app.handlers import bp as blueprint

OK = "OK"
WARNING = "WARNING"
CRITICAL = "CRITICAL"

DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def get_db_conf():
    return current_app.config.get('DATABASE')


def get_services_conf():
    return current_app.config.get('SERVICES')


def status_db_parse(db_data):
    if not db_data:
        return {}
    converted_data = []
    for row in db_data:
        converted_data.append(status_db_parse_entry(row))
    return converted_data


def status_db_parse_entry(row):
    if row and len(row) == 3 and row[0] and row[1] and row[2]:
        status = row[1]
        return {"datetime": row[0].strftime(DATE_FORMAT), "status": status, "host": row[2]}
    else:
        return None


def calculate_service_uptime(cursor, service, host, start_date, end_date):
    cursor.execute(
        f"SELECT timestamp('{start_date}'), status"
        f" FROM {get_db_conf()['status_table']}"
        f" WHERE event_time <= '{start_date}'"
        f" AND service = '{service}'"
        f" AND host = '{host}'"
        f" ORDER BY event_time DESC LIMIT 1"
    )
    first_status = cursor.fetchall()

    cursor.execute(
        f"SELECT event_time, status"
        f" FROM {get_db_conf()['status_table']}"
        f" WHERE event_time BETWEEN '{start_date}' AND '{end_date}'"
        f" AND service = '{service}'"
        f" AND host = '{host}'"
        f" ORDER BY event_time ASC"
    )
    data = cursor.fetchall()

    cursor.execute(
        f"SELECT timestamp('{end_date}'), status"
        f" FROM {get_db_conf()['status_table']}"
        f" WHERE event_time <= '{end_date}'"
        f" AND service = '{service}'"
        f" AND host = '{host}'"
        f" ORDER BY event_time DESC LIMIT 1"
    )
    last_status = cursor.fetchall()

    status_list = []
    if first_status:
        status_list.append({"time": first_status[0][0], "status": first_status[0][1]})

    if data:
        for row in data:
            event_time = row[0]
            status = row[1]
            status_list.append({"time": event_time, "status": status})

    if last_status:
        status_list.append({"time": last_status[0][0], "status": last_status[0][1]})

    status_uptime = {OK: 0, WARNING: 0, CRITICAL: 0}
    if len(status_list) == 2:
        start = status_list[0]
        end = status_list[1]
        status_uptime[start["status"]] = int((end["time"] - start["time"]).total_seconds())
    else:
        prev_status = ""
        prev_time = 0
        for status in status_list:
            if not prev_status:
                prev_status = status["status"]
                prev_time = status["time"]
                continue
            if status["status"] != prev_status:
                status_uptime[prev_status] += int((status["time"] - prev_time).total_seconds())
                prev_status = status["status"]
                prev_time = status["time"]

    if status_uptime[OK] == 0 and status_uptime[WARNING] == 0 and status_uptime[CRITICAL] == 0:
        return {}
    return status_uptime


def get_uptime_data(db_cursor, start_date, end_date, service):
    uptime_data = None
    db_cursor.execute(f"SELECT DISTINCT host FROM {get_db_conf()['status_table']}")

    for row in db_cursor.fetchall():
        host = row[0]
        status_uptime = calculate_service_uptime(
            db_cursor,
            service,
            host,
            start_date,
            end_date
        )
        if not status_uptime:
            continue
        if not uptime_data:
            uptime_data = status_uptime
        else:
            uptime_data[OK] += status_uptime[OK]
            uptime_data[WARNING] += status_uptime[WARNING]
            uptime_data[CRITICAL] += status_uptime[CRITICAL]
    total = uptime_data[OK] + uptime_data[WARNING] + uptime_data[CRITICAL]
    return {
        OK: (uptime_data[OK] + uptime_data[WARNING])/total * 100,
        CRITICAL: uptime_data[CRITICAL]/total * 100
    }


def get_status_data(db_cursor, start_date, end_date, service):
    events = []
    db_cursor.execute(f"SELECT DISTINCT host FROM {get_db_conf()['status_table']}")
    for host_row in db_cursor.fetchall():
        host = host_row[0]
        db_cursor.execute(
            f"SELECT timestamp('{start_date}'), status, host"
            f" FROM {get_db_conf()['status_table']}"
            f" WHERE event_time <= '{start_date}'"
            f" AND service = '{service}'"
            f" AND host = '{host}'"
            f" ORDER BY event_time DESC LIMIT 1"
        )
        first_status = db_cursor.fetchall()
        if first_status:
            events.append(status_db_parse_entry(first_status[0]))

    db_cursor.execute(
        f"SELECT event_time, status, host"
        f" FROM {get_db_conf()['status_table']}"
        f" WHERE event_time BETWEEN '{start_date}' AND '{end_date}'"
        f" AND service = '{service}'"
        f" ORDER BY event_time DESC"
    )

    parsed_data = status_db_parse(db_cursor.fetchall())
    if parsed_data:
        prev_status = ""
        prev_time = 0
        prev_host = ""
        for entry in parsed_data:
            if not prev_status and not prev_time and not prev_host:
                prev_status = entry["status"]
                prev_time = entry["datetime"]
                prev_host = entry["host"]
            if entry["status"] != prev_status:
                prev_status = entry["status"]
                prev_time = entry["datetime"]
                prev_host = entry["host"]
                events.append(entry)
    return events


def get_data(start_date, end_date):
    data = {}
    database = db.get_db(cfg=get_db_conf())
    db_cursor = database.cursor()
    db_cursor.execute(f"SELECT DISTINCT service FROM {get_db_conf()['status_table']}")
    for service_row in db_cursor.fetchall():
        service = service_row[0]
        config = get_services_conf()
        name = config[service] if service in config else service
        status_data = get_status_data(db_cursor, start_date, end_date, service)
        uptime_data = get_uptime_data(db_cursor, start_date, end_date, service)
        data[service] = {
            "display_name": name,
            "status_data": status_data,
            "uptime_data": uptime_data
        }
    db_cursor.close()
    database.commit()
    return data


def get_data_for_period(period):
    today = datetime.now().date()
    end_date = datetime(today.year, today.month, today.day, 23, 59, 59) - timedelta(days=1)
    if period == "DAY":
        start_date = datetime(today.year, today.month, today.day, 0, 0, 0) - timedelta(days=1)
    elif period == "MONTH":
        start_date = datetime(today.year, today.month, today.day, 0, 0, 0) - relativedelta(months=1, days=1)
    else:
        start_date = datetime(today.year, today.month, today.day, 0, 0, 0) - relativedelta(years=1, days=1)
    return get_data(start_date, end_date)


def get_data_between_dates(date_from, date_to):
    date_from = date_from + ' 00:00:00'
    date_to = date_to + ' 23:59:59'
    start_date = datetime.strptime(date_from, DATE_FORMAT)
    end_date = datetime.strptime(date_to, DATE_FORMAT)
    if end_date < start_date:
        # FIXME - generate error instead
        tmp_date = end_date
        end_date = start_date
        start_date = tmp_date

    return get_data(start_date, end_date)


@blueprint.route('/')
def home():
    return redirect(url_for('dashboard.dashboard', selected_range="past_day"))


@blueprint.route('/dashboard/<selected_range>/')
def dashboard(selected_range):
    data = []
    if selected_range == "select_date":
        date_from = request.args.get("date_from")
        date_to = request.args.get("date_to")
        if date_from is None or date_to is None:
            return render_template(
                "dashboard.html",
                selected_range="select_date",
                data=data
            )
        data = get_data_between_dates(date_from, date_to)
        return render_template(
            'dashboard.html',
            selected_range="select_date",
            data=data
        )

    range_to_sql = {"past_day": "DAY", "past_month": "MONTH", "past_year": "YEAR"}
    if selected_range not in range_to_sql.keys():
        return redirect(url_for('dashboard', selected_range="past_day"))

    data = get_data_for_period(range_to_sql[selected_range])
    return render_template(
        'dashboard.html',
        data=data,
        selected_range=selected_range
    )
