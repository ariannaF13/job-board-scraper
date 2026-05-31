"""
Flask page that runs all scraper information. 
Flask is used to convert python code into web usables

"""

from flask import Flask, render_template, request, redirect, url_for, jsonify
import Main
import sqlite3
import subprocess
import os
from dotenv import load_dotenv
load_dotenv()





#ADMIN_PASSWORD = "PA$$W0RD"
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")

app = Flask(__name__)

def get_db_connection():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn

@app.route("/")
def index():
    conn = get_db_connection()
    jobs = conn.execute("SELECT * FROM jobs ORDER BY date_scraped DESC").fetchall()
    conn.close()
    return render_template("index.html", jobs=jobs)


@app.route("/run", methods=["POST"])
def run():
    email = request.form.get("email")
    if not email:
        return redirect(url_for("index"))

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT OR IGNORE INTO subscribers (email)
        VALUES (?)
    """, (email,))

    conn.commit()
    conn.close()
    return redirect(url_for("index"))





@app.route("/admin", methods=["GET", "POST"])
def admin():
    if request.method == "POST":
        password = request.form.get("password")
        if password == ADMIN_PASSWORD:
            return render_template("admin_panel.html")
        return "Incorrect password"

    return render_template("admin_login.html")


@app.route("/admin/refresh", methods=["POST"])
def admin_refresh():
    Main.database_refresh()
    result =  "Database refresh done."
    return jsonify({"status": "ok", "message": result})


@app.route("/admin/send_emails", methods=["POST"])
def send_email():
    Main.send_all_emails()
    result = "Emails sent."
    return jsonify({"status": "ok", "message": result})



if __name__ == "__main__":
    app.run(debug=True)


