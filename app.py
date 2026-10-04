from flask import Flask, jsonify, render_template, request, send_file
import csv
import io
import os
import re
import sqlite3
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get("APPOINTMENT_DB", BASE_DIR / "instance" / "appointments.db"))
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

app = Flask(__name__)
app.config["JSON_SORT_KEYS"] = False

ALLOWED_STATUS = {"Scheduled", "Completed", "Cancelled"}


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS appointments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                phone TEXT NOT NULL,
                date TEXT NOT NULL,
                time TEXT NOT NULL,
                purpose TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Scheduled',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()


def normalize_date(value):
    value = (value or "").strip()
    if not value:
        raise ValueError("Date is required.")
    value = re.sub(r"[/.]", "-", value)
    try:
        return datetime.strptime(value, "%d-%m-%Y").strftime("%d-%m-%Y")
    except ValueError:
        raise ValueError("Date must be in DD-MM-YYYY format, for example 15-10-2026.")


def normalize_time(value):
    value = (value or "").strip()
    try:
        return datetime.strptime(value, "%H:%M").strftime("%H:%M")
    except ValueError:
        raise ValueError("Time must be in 24-hour HH:MM format, for example 10:30.")


def validate_payload(data):
    name = str(data.get("name", "")).strip()
    phone = str(data.get("phone", "")).strip()
    purpose = str(data.get("purpose", "")).strip()
    status = str(data.get("status", "Scheduled")).strip() or "Scheduled"

    if not all([name, phone, purpose]):
        raise ValueError("Please fill all appointment fields.")
    if not phone.isdigit() or not 10 <= len(phone) <= 15:
        raise ValueError("Enter a valid phone number (10-15 digits).")
    if status not in ALLOWED_STATUS:
        raise ValueError("Invalid appointment status.")

    date = normalize_date(data.get("date"))
    time = normalize_time(data.get("time"))
    return name, phone, date, time, purpose, status


def row_to_dict(row):
    return {
        "id": row["id"],
        "name": row["name"],
        "phone": row["phone"],
        "date": row["date"],
        "time": row["time"],
        "purpose": row["purpose"],
        "status": row["status"],
    }


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/appointments")
def list_appointments():
    q = request.args.get("q", "").strip()
    with get_db() as conn:
        if q:
            like = f"%{q}%"
            rows = conn.execute("""
                SELECT * FROM appointments
                WHERE name LIKE ? OR phone LIKE ? OR purpose LIKE ? OR status LIKE ? OR date LIKE ?
                ORDER BY date, time, id DESC
            """, (like, like, like, like, like)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM appointments ORDER BY date, time, id DESC").fetchall()
    return jsonify([row_to_dict(r) for r in rows])


@app.get("/api/stats")
def stats():
    with get_db() as conn:
        total = conn.execute("SELECT COUNT(*) FROM appointments").fetchone()[0]
        scheduled = conn.execute("SELECT COUNT(*) FROM appointments WHERE status='Scheduled'").fetchone()[0]
        completed = conn.execute("SELECT COUNT(*) FROM appointments WHERE status='Completed'").fetchone()[0]
        cancelled = conn.execute("SELECT COUNT(*) FROM appointments WHERE status='Cancelled'").fetchone()[0]
    return jsonify({"total": total, "scheduled": scheduled, "completed": completed, "cancelled": cancelled})


@app.post("/api/appointments")
def create_appointment():
    try:
        values = validate_payload(request.get_json(silent=True) or {})
        with get_db() as conn:
            cur = conn.execute("""
                INSERT INTO appointments (name, phone, date, time, purpose, status)
                VALUES (?, ?, ?, ?, ?, ?)
            """, values)
            row = conn.execute("SELECT * FROM appointments WHERE id=?", (cur.lastrowid,)).fetchone()
            conn.commit()
        return jsonify(row_to_dict(row)), 201
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except sqlite3.Error:
        return jsonify({"error": "Database error. Please try again."}), 500


@app.put("/api/appointments/<int:appointment_id>")
def update_appointment(appointment_id):
    try:
        values = validate_payload(request.get_json(silent=True) or {})
        with get_db() as conn:
            exists = conn.execute("SELECT id FROM appointments WHERE id=?", (appointment_id,)).fetchone()
            if not exists:
                return jsonify({"error": "Appointment not found."}), 404
            conn.execute("""
                UPDATE appointments
                SET name=?, phone=?, date=?, time=?, purpose=?, status=?
                WHERE id=?
            """, (*values, appointment_id))
            row = conn.execute("SELECT * FROM appointments WHERE id=?", (appointment_id,)).fetchone()
            conn.commit()
        return jsonify(row_to_dict(row))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except sqlite3.Error:
        return jsonify({"error": "Database error. Please try again."}), 500


@app.delete("/api/appointments/<int:appointment_id>")
def delete_appointment(appointment_id):
    with get_db() as conn:
        cur = conn.execute("DELETE FROM appointments WHERE id=?", (appointment_id,))
        conn.commit()
    if cur.rowcount == 0:
        return jsonify({"error": "Appointment not found."}), 404
    return jsonify({"message": "Appointment deleted successfully."})


@app.get("/api/export")
def export_csv():
    with get_db() as conn:
        rows = conn.execute("SELECT id, name, phone, date, time, purpose, status FROM appointments ORDER BY date, time, id").fetchall()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Name", "Phone", "Date", "Time", "Purpose", "Status"])
    for row in rows:
        writer.writerow([row[k] for k in ("id", "name", "phone", "date", "time", "purpose", "status")])
    mem = io.BytesIO(output.getvalue().encode("utf-8"))
    mem.seek(0)
    return send_file(mem, mimetype="text/csv", as_attachment=True, download_name="appointment_records.csv")


@app.get("/health")
def health():
    return jsonify({"status": "ok"})


init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
