from pathlib import Path
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash


DATABASE_PATH = Path(__file__).resolve().parent / "toa_transport.db"


def get_connection():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database():
    with get_connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS staff (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_no TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                home_location TEXT NOT NULL,
                pickup_point TEXT NOT NULL,
                route TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Active'
            );

            CREATE TABLE IF NOT EXISTS schedules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                schedule_date TEXT NOT NULL,
                departure_time TEXT NOT NULL,
                trip_type TEXT NOT NULL,
                route TEXT NOT NULL,
                vehicle TEXT NOT NULL,
                driver TEXT NOT NULL,
                destination TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Scheduled'
            );

            CREATE TABLE IF NOT EXISTS driver_assignments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                driver_name TEXT NOT NULL,
                vehicle TEXT NOT NULL,
                route TEXT NOT NULL,
                staff_assigned INTEGER NOT NULL DEFAULT 0,
                departure_time TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Assigned'
            );

            CREATE TABLE IF NOT EXISTS boarding (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                assignment_id INTEGER NOT NULL,
                staff_name TEXT NOT NULL,
                pickup_point TEXT NOT NULL,
                pickup_time TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Waiting',
                FOREIGN KEY (assignment_id) REFERENCES driver_assignments(id)
            );

            CREATE TABLE IF NOT EXISTS driver_issues (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                assignment_id INTEGER NOT NULL,
                issue_type TEXT NOT NULL,
                details TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (assignment_id) REFERENCES driver_assignments(id)
            );

            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                display_name TEXT NOT NULL,
                role TEXT NOT NULL CHECK (role IN ('ADMIN', 'STAFF', 'DRIVER')),
                staff_id INTEGER,
                driver_name TEXT
            );

            CREATE TABLE IF NOT EXISTS vehicles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                registration TEXT NOT NULL UNIQUE,
                vehicle_type TEXT NOT NULL,
                capacity INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'Available',
                assignment TEXT NOT NULL DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS routes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                origin TEXT NOT NULL,
                pickup_points TEXT NOT NULL,
                destination TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS transport_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                requester TEXT NOT NULL,
                request_type TEXT NOT NULL,
                details TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Pending',
                created_at 
                TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS driver_swaps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                original_driver TEXT NOT NULL,
                replacement_driver TEXT NOT NULL,
                vehicle TEXT NOT NULL,
                reason TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Pending',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS lateness_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                staff_name TEXT NOT NULL,
                route TEXT NOT NULL,
                minutes_late INTEGER NOT NULL,
                reason TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS meal_arrangements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                meal_date TEXT NOT NULL,
                meal_type TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                notes TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'Pending'
            );

            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recipient TEXT NOT NULL,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                notification_type TEXT NOT NULL DEFAULT 'Info',
                is_read INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS staff_confirmations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                staff_name TEXT NOT NULL UNIQUE,
                status TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        connection.executemany(
            """
            INSERT OR IGNORE INTO staff
            (employee_no, name, home_location, pickup_point, route)
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                ("TOA001", "Veronica Odhiambo", "Nyali", "Nyali Centre", "Nyali Route"),
                ("TOA002", "James Otieno", "Bamburi", "Bamburi Mwisho", "Bamburi Route"),
            ],
        )
        connection.executemany(
            """
            INSERT OR IGNORE INTO users
            (username, password_hash, display_name, role, driver_name)
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                ("admin", generate_password_hash("admin123"), "Transport Admin", "ADMIN", None),
                ("veronica", generate_password_hash("staff123"), "Veronica Odhiambo", "STAFF", None),
                ("peter", generate_password_hash("driver123"), "Peter Otieno", "DRIVER", "Peter Otieno"),
            ],
        )
        connection.executemany(
            """
            INSERT OR IGNORE INTO vehicles (registration, vehicle_type, capacity, status, assignment)
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                ("KDL 837M", "Staff Bus", 14, "On Trip", "Nyali Route"),
                ("KDA 456P", "Staff Bus", 14, "Assigned", "Bamburi Route"),
                ("KDB 789R", "Van", 8, "PM Standby", "Project Manager"),
                ("KDC 345T", "Special Vehicle", 4, "Available", "Non-Shareable"),
            ],
        )
        connection.executemany(
            "INSERT OR IGNORE INTO routes (name, origin, pickup_points, destination) VALUES (?, ?, ?, ?)",
            [
                ("Nyali Route", "Nyali", "Nyali Centre, Links Road", "TOA Site"),
                ("Bamburi Route", "Bamburi", "Bamburi Mwisho, Mtambo", "TOA Site"),
                ("Mtwapa Route", "Mtwapa", "Mtwapa Stage, Shanzu", "TOA Site"),
            ],
        )
        connection.execute(
            """
            INSERT INTO driver_assignments
            (driver_name, vehicle, route, staff_assigned, departure_time)
            SELECT ?, ?, ?, ?, ?
            WHERE NOT EXISTS (SELECT 1 FROM driver_assignments)
            """,
            ("Peter Otieno", "KBK 348C", "Mombasa -> Bamburi -> Nyali", 18, "06:30 AM"),
        )
        assignment_id = connection.execute(
            "SELECT id FROM driver_assignments ORDER BY id LIMIT 1"
        ).fetchone()[0]
        connection.executemany(
            """
            INSERT INTO boarding (assignment_id, staff_name, pickup_point, pickup_time)
            SELECT ?, ?, ?, ?
            WHERE NOT EXISTS (SELECT 1 FROM boarding WHERE assignment_id = ? AND staff_name = ?)
            """,
            [
                (assignment_id, "Jane", "Bamburi", "06:30 AM", assignment_id, "Jane"),
                (assignment_id, "Mary", "Bamburi", "06:30 AM", assignment_id, "Mary"),
                (assignment_id, "John", "Nyali", "06:40 AM", assignment_id, "John"),
            ],
        )


def list_staff():
    with get_connection() as connection:
        rows = connection.execute("SELECT * FROM staff ORDER BY id").fetchall()
    return [dict(row) for row in rows]


def add_staff(data):
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO staff
            (employee_no, name, home_location, pickup_point, route)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                data["employee_no"],
                data["name"],
                data["home_location"],
                data["pickup_point"],
                data["route"],
            ),
        )
    return cursor.lastrowid


def list_schedules():
    with get_connection() as connection:
        rows = connection.execute("SELECT * FROM schedules ORDER BY schedule_date, departure_time").fetchall()
    return [dict(row) for row in rows]


def add_schedule(data):
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO schedules
            (schedule_date, departure_time, trip_type, route, vehicle, driver, destination)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data["schedule_date"],
                data["departure_time"],
                data["trip_type"],
                data["route"],
                data["vehicle"],
                data["driver"],
                data["destination"],
            ),
        )
    return cursor.lastrowid


def get_driver_assignment():
    with get_connection() as connection:
        assignment = connection.execute(
            "SELECT * FROM driver_assignments ORDER BY id LIMIT 1"
        ).fetchone()
        boarding_rows = connection.execute(
            "SELECT * FROM boarding WHERE assignment_id = ? ORDER BY id",
            (assignment["id"],),
        ).fetchall()
    result = dict(assignment)
    result["boarding"] = [dict(row) for row in boarding_rows]
    result["boarded"] = sum(row["status"] == "Boarded" for row in boarding_rows)
    return result


def update_assignment_status(status):
    with get_connection() as connection:
        connection.execute(
            "UPDATE driver_assignments SET status = ? WHERE id = (SELECT id FROM driver_assignments ORDER BY id LIMIT 1)",
            (status,),
        )


def update_boarding(boarding_id, status):
    with get_connection() as connection:
        connection.execute("UPDATE boarding SET status = ? WHERE id = ?", (status, boarding_id))


def add_driver_issue(issue_type, details):
    with get_connection() as connection:
        assignment_id = connection.execute(
            "SELECT id FROM driver_assignments ORDER BY id LIMIT 1"
        ).fetchone()[0]
        cursor = connection.execute(
            "INSERT INTO driver_issues (assignment_id, issue_type, details) VALUES (?, ?, ?)",
            (assignment_id, issue_type, details),
        )
    return cursor.lastrowid


def find_user(username, password):
    with get_connection() as connection:
        row = connection.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    if row and check_password_hash(row["password_hash"], password):
        return dict(row)
    return None


def list_table(table):
    allowed = {"vehicles", "routes", "transport_requests", "driver_swaps", "lateness_reports", "meal_arrangements", "notifications"}
    if table not in allowed:
        raise ValueError("Unsupported table")
    with get_connection() as connection:
        rows = connection.execute(f"SELECT * FROM {table} ORDER BY id DESC").fetchall()
    return [dict(row) for row in rows]


def insert_record(table, data):
    schemas = {
        "vehicles": ("registration", "vehicle_type", "capacity", "status", "assignment"),
        "routes": ("name", "origin", "pickup_points", "destination"),
        "transport_requests": ("requester", "request_type", "details"),
        "driver_swaps": ("original_driver", "replacement_driver", "vehicle", "reason"),
        "lateness_reports": ("staff_name", "route", "minutes_late", "reason"),
        "meal_arrangements": ("meal_date", "meal_type", "quantity", "notes"),
        "notifications": ("recipient", "title", "message", "notification_type"),
    }
    fields = schemas.get(table)
    if not fields or any(data.get(field) in (None, "") for field in fields):
        raise ValueError("Required fields are missing")
    with get_connection() as connection:
        cursor = connection.execute(
            f"INSERT INTO {table} ({', '.join(fields)}) VALUES ({', '.join('?' for _ in fields)})",
            tuple(data[field] for field in fields),
        )
    return cursor.lastrowid


def save_staff_confirmation(staff_name, status):
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO staff_confirmations (staff_name, status)
            VALUES (?, ?)
            ON CONFLICT(staff_name) DO UPDATE SET status = excluded.status, updated_at = CURRENT_TIMESTAMP
            """,
            (staff_name, status),
        )


def get_staff_confirmation(staff_name):
    with get_connection() as connection:
        row = connection.execute(
            "SELECT * FROM staff_confirmations WHERE staff_name = ?", (staff_name,)
        ).fetchone()
    return dict(row) if row else None