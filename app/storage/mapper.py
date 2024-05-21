DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def status_db_parse(db_data):
    if not db_data:
        return {}
    converted_data = []
    for row in db_data:
        converted_data.append(map_event(row))
    return converted_data


def map_event(row):
    if row and len(row) == 3 and row[0] and row[1] and row[2]:
        event_time = row[0]
        status = row[1]
        host = row[2]
        return {"time": event_time, "status": status, "host": host}
    else:
        return None


def map_events(data):
    status_list = []
    if data:
        for row in data:
            event_time = row[0]
            status = row[1]
            host = row[2]
            status_list.append({"time": event_time, "status": status, "host": host})
    return status_list
