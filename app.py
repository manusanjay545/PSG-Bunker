from flask import Flask, render_template, request, jsonify, send_file
from bunker_mod import return_attendance, data_json, return_cgpa
import math

app = Flask(__name__)
sessions = {}

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/login", methods=["POST"])
def login():
    body = request.get_json()
    roll = body["rollno"]
    pwd = body["password"]
    data = return_attendance(roll, pwd)

    if isinstance(data, str):
        return jsonify({"ok": False, "message": data})
    else:
        att, session = data
        sessions[roll] = session
        app.config["last_att"] = att
        app.config["last_roll"] = roll
        return jsonify({"ok": True})

@app.route("/attendance")
def attendance():
    att = app.config.get("last_att")
    if not att:
        return jsonify({"error": "No data"})

    json_data = data_json(att)
    total = sum(i['total_hours'] for i in json_data)
    present = sum(i['total_present'] for i in json_data)
    pct = (present / total) * 100 if total else 0

    res = {
        "total_days": total,
        "attended_days": present,
        "percentage": pct,
        "subjects": json_data
    }

    if pct < 75:
        res['need_days'] = math.ceil((0.75 * total - present) / (1 - 0.75))
    else:
        res['bunkable_days'] = math.floor((present - 0.75 * total) / 0.75)

    return jsonify(res)

@app.route("/cgpa")
def cgpa():
    roll = app.config.get("last_roll")
    session = sessions.get(roll)
    if not session:
        return jsonify({"error": "Session expired"})

    res = return_cgpa(session)
    return jsonify(res)

@app.route("/robots.txt")
def robots():
    return send_file("robots.txt")

@app.route("/sitemap.xml")
def sitemap():
    return send_file("sitemap.xml")

if __name__ == "__main__":
    app.run(debug=True)
