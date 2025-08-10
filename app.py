
import os
import math
from flask import Flask, render_template, request, jsonify, session as flask_session, send_from_directory
from bunker_mod import return_attendance, data_json, return_cgpa, get_timetable_data

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'psg-bunker-secret-key-change-in-production')

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login', methods=['POST'])
def login():
    # Handle both form and JSON data
    if request.is_json:
        rollno = request.json.get('rollno')
        password = request.json.get('password')
    else:
        rollno = request.form.get('rollno')
        password = request.form.get('password')

    if not rollno or not password:
        if request.is_json:
            return jsonify({"ok": False, "message": "Roll number and password are required"})
        else:
            return render_template("index.html", error="Roll number and password are required")

    result = return_attendance(rollno, password)

    if isinstance(result, str):
        if request.is_json:
            return jsonify({"ok": False, "message": result})
        else:
            return render_template("index.html", error=result)

    attendance_raw, session = result
    attendance_data = data_json(attendance_raw)
    cgpa_data = return_cgpa(session)
    timetable_data = get_timetable_data()

    # Store data in Flask session for API endpoints
    flask_session['attendance_data'] = attendance_data
    flask_session['cgpa_data'] = cgpa_data
    flask_session['timetable_data'] = timetable_data
    flask_session['rollno'] = rollno

    if request.is_json:
        return jsonify({"ok": True})
    else:
        return render_template("dashboard.html",
                             rollno=rollno,
                             attendance=attendance_data,
                             cgpa=cgpa_data,
                             timetable=timetable_data)

@app.route('/attendance')
def get_attendance():
    """API endpoint for attendance data"""
    attendance_data = flask_session.get('attendance_data', [])

    if not attendance_data:
        return jsonify({"error": "No attendance data available"})

    # Calculate overall statistics
    total_hours = sum(subject['total_hours'] for subject in attendance_data)
    total_present = sum(subject['total_present'] for subject in attendance_data)
    overall_percentage = (total_present / total_hours * 100) if total_hours > 0 else 0

    # Calculate bunkable/need days for 75% threshold
    if overall_percentage < 75:
        need_days = math.ceil((0.75 * total_hours - total_present) / 0.25)
        bunkable_days = 0
    else:
        need_days = 0
        bunkable_days = int((total_present - 0.75 * total_hours) / 0.75)

    return jsonify({
        "subjects": attendance_data,
        "total_days": total_hours,
        "attended_days": total_present,
        "percentage": overall_percentage,
        "need_days": need_days,
        "bunkable_days": bunkable_days
    })

@app.route('/cgpa')
def get_cgpa():
    """API endpoint for CGPA data"""
    cgpa_data = flask_session.get('cgpa_data', {})
    return jsonify(cgpa_data)

@app.route('/timetable')
def get_timetable():
    """API endpoint for timetable data"""
    timetable_data = flask_session.get('timetable_data', {})
    attendance_data = flask_session.get('attendance_data', [])

    # Create attendance lookup for color coding
    attendance_lookup = {}
    for subject in attendance_data:
        attendance_lookup[subject['name']] = subject['percentage_of_attendance']

    # Add attendance percentage to timetable data
    for day in timetable_data:
        for slot in timetable_data[day]:
            subject_name = slot['subject']
            slot['attendance_percentage'] = attendance_lookup.get(subject_name, 100)

            # Add color class based on attendance
            if slot['attendance_percentage'] < 75:
                slot['color_class'] = 'danger'
            elif slot['attendance_percentage'] < 85:
                slot['color_class'] = 'warning'  
            else:
                slot['color_class'] = 'success'

    return jsonify(timetable_data)

@app.route('/dashboard')
def dashboard():
    """Dashboard page route"""
    if 'rollno' not in flask_session:
        return redirect('/')

    return render_template("dashboard.html",
                         rollno=flask_session['rollno'],
                         attendance=flask_session.get('attendance_data', []),
                         cgpa=flask_session.get('cgpa_data', {}),
                         timetable=flask_session.get('timetable_data', {}))

@app.route('/robots.txt')
def robots():
    return send_from_directory(app.static_folder, 'robots.txt')

@app.route('/sitemap.xml')
def sitemap():
    return send_from_directory(app.static_folder, 'sitemap.xml')

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(app.static_folder, 'favicon.ico')

@app.route('/logo.ico')
def logo():
    return send_from_directory(app.static_folder, 'favicon.ico')

@app.route("/calendar")
def calendar_page():
    return render_template("calendar.html")

# Error handlers
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
