from flask import redirect, url_for, request, render_template

from app.handlers import bp as blueprint
from app.service import service

PARAM_RANGE_MAP = {"past_day": "DAY", "past_month": "MONTH", "past_year": "YEAR"}


@blueprint.route('/')
def home():
    return redirect(url_for('dashboard.dashboard', selected_range="past_day"))


@blueprint.route('/dashboard/<selected_range>/')
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
