from flask import Flask, render_template, request
from bunker_mod import return_attendance, data_json, return_cgpa

app = Flask(__name__)

@app.route('/')
def home():
    return render_template("index.html")

@app.route('/attendance', methods=['POST'])
def attendance():
    rollno = request.form['rollno']
    password = request.form['password']

    result = return_attendance(rollno, password)

    if isinstance(result, str):
        return render_template("index.html", error=result)

    attendance_data_raw, session = result
    attendance_data = data_json(attendance_data_raw)

    return render_template("attendance.html", data=attendance_data)

@app.route('/cgpa', methods=['POST'])
def cgpa():
    rollno = request.form['rollno']
    password = request.form['password']

    result = return_attendance(rollno, password)

    if isinstance(result, str):
        return render_template("index.html", error=result)

    _, session = result
    cgpa_data = return_cgpa(session)

    return render_template("cgpa.html", cgpa=cgpa_data)

if __name__ == "__main__":
    app.run(debug=True)
