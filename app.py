from flask import Flask, render_template, request, redirect, url_for
from bunker_mod import return_attendance, data_json, return_cgpa

app = Flask(__name__)

@app.route('/')
def login_page():
    return render_template('index.html')  # Ensure this file is in templates/

@app.route('/attendance', methods=['POST'])
def attendance():
    username = request.form['rollno']
    password = request.form['password']

    result = return_attendance(username, password)

    if isinstance(result, str):
        # Return error from server (invalid password, etc.)
        return render_template("index.html", error=result)

    attendance_data_raw, session = result
    attendance_data = data_json(attendance_data_raw)

    return render_template('attendance.html', data=attendance_data)

@app.route('/cgpa', methods=['POST'])
def cgpa():
    username = request.form['rollno']
    password = request.form['password']

    result = return_attendance(username, password)

    if isinstance(result, str):
        return render_template("index.html", error=result)

    _, session = result
    cgpa_data = return_cgpa(session)

    return render_template('cgpa.html', cgpa=cgpa_data)

if __name__ == '__main__':
    app.run(debug=True)
