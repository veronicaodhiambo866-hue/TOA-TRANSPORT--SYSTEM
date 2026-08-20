from functools import wraps


from flask import Flask, jsonify, redirect, request, send_from_directory, session, url_for

from DATABASE import (
    add_driver_issue,
    add_schedule,
    add_staff,
    find_user,
    get_driver_assignment,
    initialize_database,
    insert_record,
    list_table,
    list_schedules,
    list_staff,
    get_staff_confirmation,
    save_staff_confirmation,
    update_assignment_status,
    update_boarding,
)


app = Flask(__name__)
app.secret_key = "toa-local-development-key"
PROJECT_DIR = app.root_path
initialize_database()


def requires_role(*roles):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            role = session.get("role")
            if role not in roles:
                return jsonify({"error": "Authentication required."}), 401
            return view(*args, **kwargs)
        return wrapped
    return decorator


@app.get("/")
def dashboard_page():
    if session.get("role") not in {None, "ADMIN"}:
        return redirect(url_for("staff_page" if session.get("role") == "STAFF" else "driver_page"))
    if session.get("role") is None:
        return redirect(url_for("login_page"))
    return send_from_directory(PROJECT_DIR, "TOA FRONTEND.HTML")


@app.get("/login")
def login_page():
    return send_from_directory(PROJECT_DIR, "LOGIN.HTML")


@app.post("/api/login")
def login():
    data = request.get_json(silent=True) or request.form
    user = find_user(data.get("username", ""), data.get("password", ""))
    if not user:
        return jsonify({"error": "Invalid username or password."}), 401
    session.clear()
    session["user_id"] = user["id"]
    session["display_name"] = user["display_name"]
    session["role"] = user["role"]
    return jsonify({"role": user["role"], "redirect": url_for({"ADMIN": "dashboard_page", "STAFF": "staff_page", "DRIVER": "driver_page"}[user["role"]])})


@app.post("/api/logout")
def logout():
    session.clear()
    return jsonify({"ok": True})


@app.get("/driver")
def driver_page():
    if session.get("role") not in {"DRIVER"}:
        if session.get("role") is None:
            return redirect(url_for("login_page"))
        return redirect(url_for("dashboard_page" if session.get("role") == "ADMIN" else "staff_page"))
    return send_from_directory(PROJECT_DIR, "DRIVER PORTAL.HTML")


@app.get("/staff")
def staff_page():
    if session.get("role") not in {"STAFF"}:
        if session.get("role") is None:
            return redirect(url_for("login_page"))
        return redirect(url_for("dashboard_page" if session.get("role") == "ADMIN" else "driver_page"))
    return send_from_directory(PROJECT_DIR, "STAFF PORTAL.HTML")


@app.get("/api/driver/assignment")
@requires_role("DRIVER")
def driver_assignment():
    return jsonify(get_driver_assignment())


@app.post("/api/driver/trip")
@requires_role("DRIVER")
def update_driver_trip():
    data = request.get_json(silent=True) or {}
    status = data.get("status")
    if status not in {"In Progress", "Completed"}:
        return jsonify({"error": "Trip status must be In Progress or Completed."}), 400
    update_assignment_status(status)
    return jsonify(get_driver_assignment())


@app.post("/api/driver/boarding/<int:boarding_id>")
@requires_role("DRIVER")
def update_driver_boarding(boarding_id):
    data = request.get_json(silent=True) or {}
    status = data.get("status")
    if status not in {"Boarded", "Waiting", "Did not board"}:
        return jsonify({"error": "Invalid boarding status."}), 400
    update_boarding(boarding_id, status)
    return jsonify(get_driver_assignment())


@app.post("/api/driver/issues")
@requires_role("DRIVER")
def report_driver_issue():
    data = request.get_json(silent=True) or {}
    if not data.get("issue_type") or not data.get("details"):
        return jsonify({"error": "Issue type and details are required."}), 400
    issue_id = add_driver_issue(data["issue_type"], data["details"])
    return jsonify({"id": issue_id}), 201


@app.get("/api/staff/me")
@requires_role("STAFF")
def staff_me():
    name = session.get("display_name", "Staff member")
    return jsonify({"display_name": name, "confirmation": get_staff_confirmation(name)})


@app.post("/api/staff/confirmation")
@requires_role("STAFF")
def staff_confirmation():
    data = request.get_json(silent=True) or {}
    status = data.get("status")
    if status not in {"Confirmed", "Not travelling"}:
        return jsonify({"error": "Invalid pickup status."}), 400
    save_staff_confirmation(session.get("display_name", "Staff member"), status)
    return jsonify({"status": status})


@app.post("/api/staff/problem")
@requires_role("STAFF")
def staff_problem():
    data = request.get_json(silent=True) or {}
    details = data.get("details", "").strip()
    if not details:
        return jsonify({"error": "Problem details are required."}), 400
    issue_id = insert_record(
        "transport_requests",
        {
            "requester": session.get("display_name", "Staff member"),
            "request_type": "Staff transport problem",
            "details": details,
        },
    )
    return jsonify({"id": issue_id}), 201


@app.get("/api/staff")
@requires_role("ADMIN", "STAFF")
def get_staff():
    return jsonify(list_staff())


@app.post("/api/staff")
@requires_role("ADMIN")
def create_staff():
    data = request.get_json(silent=True) or {}
    required_fields = ("employee_no", "name", "home_location", "pickup_point", "route")
    if any(not data.get(field) for field in required_fields):
        return jsonify({"error": "All staff fields are required."}), 400
    try:
        staff_id = add_staff(data)
    except Exception as error:
        return jsonify({"error": str(error)}), 400
    return jsonify({"id": staff_id}), 201


@app.get("/api/schedules")
@requires_role("ADMIN", "STAFF")
def get_schedules():
    return jsonify(list_schedules())


@app.post("/api/schedules")
@requires_role("ADMIN")
def create_schedule():
    data = request.get_json(silent=True) or {}
    required_fields = (
        "schedule_date",
        "departure_time",
        "trip_type",
        "route",
        "vehicle",
        "driver",
        "destination",
    )
    if any(not data.get(field) for field in required_fields):
        return jsonify({"error": "All schedule fields are required."}), 400
    schedule_id = add_schedule(data)
    return jsonify({"id": schedule_id}), 201


@app.get("/api/admin/<table>")
@requires_role("ADMIN")
def admin_list(table):
    try:
        return jsonify(list_table(table))
    except ValueError as error:
        return jsonify({"error": str(error)}), 404


@app.post("/api/admin/<table>")
@requires_role("ADMIN", "STAFF")
def admin_create(table):
    try:
        record_id = insert_record(table, request.get_json(silent=True) or {})
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    except Exception as error:
        return jsonify({"error": str(error)}), 400
    return jsonify({"id": record_id}), 201


if __name__ == "__main__":
    app.run(debug=True)