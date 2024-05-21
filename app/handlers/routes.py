from datetime import datetime

from flask import redirect, url_for, request, render_template, current_app
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import check_password_hash

from app.handlers import bp as blueprint
from app.service import service
from app.service.service import STATUSES

PARAM_RANGE_MAP = {"past_day": "DAY", "past_month": "MONTH", "past_year": "YEAR"}

auth = HTTPBasicAuth()


@auth.verify_password
def verify_password(username, password):
    users = current_app.config.get("WEB_SECURITY_USERS")
    if username in users and check_password_hash(users.get(username), password):
        return username


@blueprint.get('/')
def home():
    return redirect(url_for('dashboard.dashboard', selected_range="past_day"))


@blueprint.route('/api/write', methods=['POST', 'PUT', 'PATCH'])
@auth.login_required
def api_write():
    request_data = request.get_json()
    if "host" not in request_data:
        return "Missing field 'host' in the input JSON", 400
    elif "status" not in request_data:
        return "Missing field 'status' in the input JSON", 400
    elif "service" not in request_data:
        return "Missing field 'service' in the input JSON", 400

    host = request_data["host"]
    if not host or len(host.strip()) == 0:
        return "Host must be specified", 400

    status = request_data["status"]
    if not status or len(status.strip()) == 0:
        return "Status must be specified", 400

    monitored_service = request_data["service"]
    if not monitored_service or len(monitored_service.strip()) == 0:
        return "Service must be specified", 400

    if status not in STATUSES:
        return f"Unknown status passed, must be one of {'.'.join(STATUSES)}", 400
    service.insert_record(host, status, monitored_service)
    return "OK", 201


@blueprint.get('/dashboard/<selected_range>/')
def dashboard(selected_range):
    data = {}
    if selected_range == "select_date":
        date_from = request.args.get("date_from")
        date_to = request.args.get("date_to")
        if date_from is None or date_to is None:
            return render_template(
                "dashboard.html",
                selected_range="select_date",
                data=data
            )
        else:
            data = service.get_data_between_dates(date_from, date_to)
            return render_template(
                'dashboard.html',
                selected_range="select_date",
                data=data
            )
    if selected_range not in PARAM_RANGE_MAP.keys():
        return redirect(url_for('dashboard', selected_range="past_day"))
    else:
        data = service.get_data_for_period(PARAM_RANGE_MAP[selected_range])
        return render_template(
            'dashboard.html',
            data=data,
            selected_range=selected_range
        )
