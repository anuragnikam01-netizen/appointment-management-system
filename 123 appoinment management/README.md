# Appointment Management System

A responsive, full-stack semester project built with **Flask + SQLite + HTML/CSS/JavaScript**.

## Features
- Responsive professional dashboard for desktop, tablet and mobile
- Add, edit and delete appointments
- Search by name, phone, purpose, status or date
- Appointment status: Scheduled, Completed, Cancelled
- Date validation with automatic normalization (`DD-MM-YYYY`, `/`, or `.` separators)
- 24-hour time validation (`HH:MM`)
- Phone validation (10–15 digits)
- Dashboard statistics
- CSV export
- SQLite database
- Health endpoint for deployment checks

## Run locally
```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
python app.py
```

Open `http://127.0.0.1:5000`.

## Deployment
The app listens on `0.0.0.0` and uses `$PORT`, so it can be deployed on a Python-compatible web host. The repository is also suitable for GitHub version control.

> For a public production system containing real personal data, add authentication and a managed database before publishing.
