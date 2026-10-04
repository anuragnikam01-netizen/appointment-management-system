import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sqlite3
import csv
from datetime import datetime
from pathlib import Path


class AppointmentManagementSystem:
    def __init__(self, root):
        self.root = root
        self.root.title("Appointment Management System")
        self.root.geometry("1050x700")
        self.root.minsize(950, 620)

        self.db_path = Path(__file__).with_name("appointment_management.db")
        self.selected_id = None

        self.name_var = tk.StringVar()
        self.phone_var = tk.StringVar()
        self.date_var = tk.StringVar()
        self.time_var = tk.StringVar()
        self.purpose_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Scheduled")
        self.search_var = tk.StringVar()
        self.status_message = tk.StringVar(value="Ready")

        self.setup_style()
        self.setup_database()
        self.create_widgets()
        self.load_appointments()

    # ---------------- DATABASE ----------------

    def get_connection(self):
        return sqlite3.connect(self.db_path)

    def setup_database(self):
        """Create the database and safely add missing columns if an old DB exists."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS appointments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    phone TEXT NOT NULL,
                    date TEXT NOT NULL,
                    time TEXT NOT NULL,
                    purpose TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'Scheduled'
                )
            """)

            # Protect against an older database with a different schema.
            cursor.execute("PRAGMA table_info(appointments)")
            existing_columns = {row[1] for row in cursor.fetchall()}

            required_columns = {
                "name": "TEXT NOT NULL DEFAULT ''",
                "phone": "TEXT NOT NULL DEFAULT ''",
                "date": "TEXT NOT NULL DEFAULT ''",
                "time": "TEXT NOT NULL DEFAULT ''",
                "purpose": "TEXT NOT NULL DEFAULT ''",
                "status": "TEXT NOT NULL DEFAULT 'Scheduled'",
            }

            for column, definition in required_columns.items():
                if column not in existing_columns:
                    cursor.execute(
                        f"ALTER TABLE appointments ADD COLUMN {column} {definition}"
                    )

            conn.commit()

    # ---------------- UI ----------------

    def setup_style(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure("Title.TLabel", font=("Segoe UI", 22, "bold"))
        style.configure("Subtitle.TLabel", font=("Segoe UI", 10))
        style.configure("Section.TLabelframe.Label", font=("Segoe UI", 11, "bold"))
        style.configure("TButton", font=("Segoe UI", 10), padding=(10, 6))
        style.configure("Treeview", font=("Segoe UI", 10), rowheight=30)
        style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"))

    def create_widgets(self):
        header = tk.Frame(self.root, bg="#1f4e78", height=95)
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(
            header,
            text="APPOINTMENT MANAGEMENT SYSTEM",
            font=("Segoe UI", 22, "bold"),
            fg="white",
            bg="#1f4e78",
        ).pack(pady=(16, 2))

        tk.Label(
            header,
            text="Manage, search and maintain appointment records",
            font=("Segoe UI", 10),
            fg="white",
            bg="#1f4e78",
        ).pack()

        main = ttk.Frame(self.root, padding=15)
        main.pack(fill="both", expand=True)

        form = ttk.LabelFrame(main, text="Appointment Details", padding=15)
        form.pack(fill="x")

        ttk.Label(form, text="Name").grid(
            row=0, column=0, sticky="w", padx=8, pady=7
        )
        ttk.Entry(form, textvariable=self.name_var, width=28).grid(
            row=0, column=1, sticky="ew", padx=8, pady=7
        )

        ttk.Label(form, text="Phone").grid(
            row=0, column=2, sticky="w", padx=8, pady=7
        )
        ttk.Entry(form, textvariable=self.phone_var, width=28).grid(
            row=0, column=3, sticky="ew", padx=8, pady=7
        )

        ttk.Label(form, text="Date (DD-MM-YYYY)").grid(
            row=1, column=0, sticky="w", padx=8, pady=7
        )
        ttk.Entry(form, textvariable=self.date_var, width=28).grid(
            row=1, column=1, sticky="ew", padx=8, pady=7
        )

        ttk.Label(form, text="Time (HH:MM)").grid(
            row=1, column=2, sticky="w", padx=8, pady=7
        )
        ttk.Entry(form, textvariable=self.time_var, width=28).grid(
            row=1, column=3, sticky="ew", padx=8, pady=7
        )

        ttk.Label(form, text="Purpose").grid(
            row=2, column=0, sticky="w", padx=8, pady=7
        )
        ttk.Entry(form, textvariable=self.purpose_var, width=28).grid(
            row=2, column=1, sticky="ew", padx=8, pady=7
        )

        ttk.Label(form, text="Status").grid(
            row=2, column=2, sticky="w", padx=8, pady=7
        )
        self.status_combo = ttk.Combobox(
            form,
            textvariable=self.status_var,
            values=("Scheduled", "Completed", "Cancelled"),
            state="readonly",
            width=25,
        )
        self.status_combo.grid(
            row=2, column=3, sticky="ew", padx=8, pady=7
        )

        form.columnconfigure(1, weight=1)
        form.columnconfigure(3, weight=1)

        button_frame = ttk.Frame(main)
        button_frame.pack(fill="x", pady=(10, 10))

        ttk.Button(
            button_frame, text="Add Appointment",
            command=self.add_appointment
        ).pack(side="left", padx=4)

        ttk.Button(
            button_frame, text="Update",
            command=self.update_appointment
        ).pack(side="left", padx=4)

        ttk.Button(
            button_frame, text="Delete",
            command=self.delete_appointment
        ).pack(side="left", padx=4)

        ttk.Button(
            button_frame, text="Clear",
            command=self.clear_form
        ).pack(side="left", padx=4)

        ttk.Button(
            button_frame, text="Export CSV",
            command=self.export_csv
        ).pack(side="left", padx=4)

        search_frame = ttk.LabelFrame(
            main, text="Search Appointments", padding=10
        )
        search_frame.pack(fill="x", pady=(0, 10))

        ttk.Label(
            search_frame, text="Search by name, phone or purpose:"
        ).pack(side="left", padx=(0, 8))

        search_entry = ttk.Entry(
            search_frame, textvariable=self.search_var, width=45
        )
        search_entry.pack(side="left", padx=5)
        search_entry.bind("<Return>", lambda event: self.search_appointments())

        ttk.Button(
            search_frame, text="Search",
            command=self.search_appointments
        ).pack(side="left", padx=5)

        ttk.Button(
            search_frame, text="Show All",
            command=self.load_appointments
        ).pack(side="left", padx=5)

        table_frame = ttk.LabelFrame(
            main, text="Appointment Records", padding=8
        )
        table_frame.pack(fill="both", expand=True)

        columns = ("ID", "Name", "Phone", "Date", "Time", "Purpose", "Status")
        self.tree = ttk.Treeview(
            table_frame, columns=columns, show="headings"
        )

        widths = {
            "ID": 55,
            "Name": 145,
            "Phone": 125,
            "Date": 105,
            "Time": 85,
            "Purpose": 220,
            "Status": 110,
        }

        for column in columns:
            self.tree.heading(column, text=column)
            self.tree.column(
                column, width=widths[column],
                anchor="center", minwidth=50
            )

        scrollbar_y = ttk.Scrollbar(
            table_frame, orient="vertical", command=self.tree.yview
        )
        scrollbar_x = ttk.Scrollbar(
            table_frame, orient="horizontal", command=self.tree.xview
        )

        self.tree.configure(
            yscrollcommand=scrollbar_y.set,
            xscrollcommand=scrollbar_x.set,
        )

        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar_y.grid(row=0, column=1, sticky="ns")
        scrollbar_x.grid(row=1, column=0, sticky="ew")

        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)

        self.tree.bind("<<TreeviewSelect>>", self.select_appointment)

        ttk.Label(
            main, textvariable=self.status_message, anchor="w"
        ).pack(fill="x", pady=(6, 0))

    # ---------------- VALIDATION ----------------

    def validate_form(self):
        name = self.name_var.get().strip()
        phone = self.phone_var.get().strip()
        date_text = self.date_var.get().strip()
        time_text = self.time_var.get().strip()
        purpose = self.purpose_var.get().strip()

        if not all((name, phone, date_text, time_text, purpose)):
            messagebox.showwarning(
                "Validation",
                "Please fill all appointment fields."
            )
            return False

        if not phone.isdigit() or not 10 <= len(phone) <= 15:
            messagebox.showwarning(
                "Validation",
                "Enter a valid phone number (10-15 digits)."
            )
            return False

        # Date: accept DD-MM-YYYY, and also normalize / or . to -.
        normalized_date = date_text.replace("/", "-").replace(".", "-")

        try:
            parsed_date = datetime.strptime(
                normalized_date, "%d-%m-%Y"
            )
            self.date_var.set(parsed_date.strftime("%d-%m-%Y"))
        except ValueError:
            messagebox.showwarning(
                "Validation",
                "Date must be in DD-MM-YYYY format.\n"
                "Example: 15-10-2026"
            )
            return False

        try:
            parsed_time = datetime.strptime(time_text, "%H:%M")
            self.time_var.set(parsed_time.strftime("%H:%M"))
        except ValueError:
            messagebox.showwarning(
                "Validation",
                "Time must be in 24-hour HH:MM format.\n"
                "Example: 10:30"
            )
            return False

        return True

    # ---------------- CRUD ----------------

    def add_appointment(self):
        if not self.validate_form():
            return

        values = (
            self.name_var.get().strip(),
            self.phone_var.get().strip(),
            self.date_var.get().strip(),
            self.time_var.get().strip(),
            self.purpose_var.get().strip(),
            self.status_var.get(),
        )

        try:
            with self.get_connection() as conn:
                conn.execute("""
                    INSERT INTO appointments
                    (name, phone, date, time, purpose, status)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, values)
                conn.commit()

            self.refresh_table()
            self.clear_form()
            self.status_message.set("Appointment added successfully.")
            messagebox.showinfo(
                "Success", "Appointment added successfully."
            )
        except sqlite3.Error as error:
            messagebox.showerror(
                "Database Error",
                f"Could not add appointment.\n\n{error}"
            )

    def update_appointment(self):
        if self.selected_id is None:
            messagebox.showwarning(
                "Update",
                "Please select an appointment from the table first."
            )
            return

        if not self.validate_form():
            return

        values = (
            self.name_var.get().strip(),
            self.phone_var.get().strip(),
            self.date_var.get().strip(),
            self.time_var.get().strip(),
            self.purpose_var.get().strip(),
            self.status_var.get(),
            self.selected_id,
        )

        try:
            with self.get_connection() as conn:
                cursor = conn.execute("""
                    UPDATE appointments
                    SET name = ?, phone = ?, date = ?, time = ?,
                        purpose = ?, status = ?
                    WHERE id = ?
                """, values)
                conn.commit()

            if cursor.rowcount == 0:
                messagebox.showwarning(
                    "Update", "The selected appointment was not found."
                )
                return

            self.refresh_table()
            self.clear_form()
            self.status_message.set("Appointment updated successfully.")
            messagebox.showinfo(
                "Success", "Appointment updated successfully."
            )
        except sqlite3.Error as error:
            messagebox.showerror(
                "Database Error",
                f"Could not update appointment.\n\n{error}"
            )

    def delete_appointment(self):
        if self.selected_id is None:
            messagebox.showwarning(
                "Delete",
                "Please select an appointment from the table first."
            )
            return

        confirm = messagebox.askyesno(
            "Confirm Delete",
            "Are you sure you want to delete this appointment?"
        )
        if not confirm:
            return

        try:
            with self.get_connection() as conn:
                conn.execute(
                    "DELETE FROM appointments WHERE id = ?",
                    (self.selected_id,)
                )
                conn.commit()

            self.refresh_table()
            self.clear_form()
            self.status_message.set("Appointment deleted successfully.")
            messagebox.showinfo(
                "Success", "Appointment deleted successfully."
            )
        except sqlite3.Error as error:
            messagebox.showerror(
                "Database Error",
                f"Could not delete appointment.\n\n{error}"
            )

    # ---------------- TABLE / SEARCH ----------------

    def load_appointments(self):
        self.search_var.set("")
        self.refresh_table()

    def refresh_table(self, search_text=""):
        for item in self.tree.get_children():
            self.tree.delete(item)

        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                if search_text:
                    pattern = f"%{search_text}%"
                    cursor.execute("""
                        SELECT id, name, phone, date, time, purpose, status
                        FROM appointments
                        WHERE name LIKE ?
                           OR phone LIKE ?
                           OR purpose LIKE ?
                        ORDER BY id DESC
                    """, (pattern, pattern, pattern))
                else:
                    cursor.execute("""
                        SELECT id, name, phone, date, time, purpose, status
                        FROM appointments
                        ORDER BY id DESC
                    """)

                rows = cursor.fetchall()

            for row in rows:
                self.tree.insert("", "end", values=row)

            self.status_message.set(
                f"{len(rows)} appointment record(s) found."
            )
        except sqlite3.Error as error:
            messagebox.showerror(
                "Database Error",
                f"Could not load appointments.\n\n{error}"
            )

    def search_appointments(self):
        text = self.search_var.get().strip()
        self.refresh_table(text)

    def select_appointment(self, event=None):
        selected = self.tree.selection()
        if not selected:
            return

        values = self.tree.item(selected[0], "values")
        if not values:
            return

        self.selected_id = int(values[0])
        self.name_var.set(values[1])
        self.phone_var.set(values[2])
        self.date_var.set(values[3])
        self.time_var.set(values[4])
        self.purpose_var.set(values[5])
        self.status_var.set(values[6])
        self.status_message.set(
            f"Selected appointment ID {self.selected_id}."
        )

    # ---------------- OTHER FEATURES ----------------

    def clear_form(self):
        self.selected_id = None
        self.name_var.set("")
        self.phone_var.set("")
        self.date_var.set("")
        self.time_var.set("")
        self.purpose_var.set("")
        self.status_var.set("Scheduled")

        for item in self.tree.selection():
            self.tree.selection_remove(item)

        self.status_message.set("Form cleared.")

    def export_csv(self):
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, name, phone, date, time, purpose, status
                    FROM appointments
                    ORDER BY id
                """)
                rows = cursor.fetchall()

            if not rows:
                messagebox.showinfo(
                    "Export CSV",
                    "There are no appointment records to export."
                )
                return

            file_path = filedialog.asksaveasfilename(
                title="Save Appointment Records",
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
            )

            if not file_path:
                return

            with open(
                file_path, "w", newline="", encoding="utf-8-sig"
            ) as csv_file:
                writer = csv.writer(csv_file)
                writer.writerow(
                    ["ID", "Name", "Phone", "Date", "Time", "Purpose", "Status"]
                )
                writer.writerows(rows)

            self.status_message.set(
                f"Exported {len(rows)} record(s) to CSV."
            )
            messagebox.showinfo(
                "Export Successful",
                f"Appointment records exported successfully.\n\n{file_path}"
            )
        except (sqlite3.Error, OSError) as error:
            messagebox.showerror(
                "Export Error",
                f"Could not export records.\n\n{error}"
            )


def main():
    root = tk.Tk()
    AppointmentManagementSystem(root)
    root.mainloop()


if __name__ == "__main__":
    main()
