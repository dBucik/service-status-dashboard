from datetime import datetime, timedelta

from dateutil.relativedelta import relativedelta
from flask import current_app

from app.storage import db

OK = "OK"
WARNING = "WARNING"
CRITICAL = "CRITICAL"

DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def get_services_conf():
    return current_app.config.get('SERVICES')


def calculate_downtime(host_events):
    events = list(host_events)
    events = sorted(events, key=lambda x: x["time"])

    downtime = 0
    in_crit = set()
    crit_start_time = 0
    for event in events:
        host = event["host"]
        status = event["status"]
        time = event["time"]
        if status == CRITICAL and not crit_start_time:
            if len(in_crit) == 0:
                crit_start_time = time
            in_crit.add(host)
        else:
            if len(in_crit) > 0 and host in in_crit:
                in_crit.remove(host)
                if len(in_crit) == 0:
                    downtime += (time - crit_start_time).total_seconds()
                    crit_start_time = None
    return downtime


def get_uptime_data(events_by_host, total_duration):
    uptime_data = {
        OK: 0,
        WARNING: 0,
        CRITICAL: 0
    }
    all_events = []
    for host, host_events in events_by_host.items():
        all_events += list(host_events)

    downtime = calculate_downtime(all_events)

    uptime_data[CRITICAL] += downtime / total_duration.total_seconds() * 100
    uptime_data[OK] += 100 - uptime_data[CRITICAL]

    return uptime_data


def get_status_data(event_by_host_data):
    res = {}
    for host, host_events in event_by_host_data.items():
        res[host] = []
        prev_event = None
        for event in host_events:
            host = event["host"]
            if not prev_event:
                prev_event = event
                res[host].append(event)
            if event["status"] != prev_event["status"]:
                prev_event = event
                res[host].append(event)
    for _, events_of_host in res.items():
        events_of_host.reverse()
    return res


def get_event_data_by_hosts(start_date, end_date, service):
    data_by_host = {}
    for host in db.get_hosts():
        first_status = db.get_event_with_earliest_before_status(host, service, start_date)
        events = db.get_events_between(host, service, start_date, end_date)
        last_status = db.get_event_with_earliest_before_status(host, service, end_date)

        event_list = []
        if first_status:
            event_list.append(first_status)

        if events:
            for event in events:
                event_list.append(event)

        if last_status:
            event_list.append(last_status)

        data_by_host[host] = event_list
    return data_by_host


def get_data(start_date, end_date):
    data = {}
    services = db.get_services()
    for service in services:
        config = get_services_conf()
        name = config[service] if service in config else service
        event_data = get_event_data_by_hosts(start_date, end_date, service)
        status_data = get_status_data(event_data)
        uptime_data = get_uptime_data(event_data, end_date - start_date)
        data[service] = {
            "display_name": name,
            "status_data": status_data,
            "uptime_data": uptime_data
        }
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