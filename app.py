from flask import Flask, render_template, request, redirect, url_for
from bunker_mod import return_attendance, return_cgpa, data_json

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login', methods=['POST'])
def login():
    rollno = request.form['rollno']
    password = request.form['password']

    raw_data, session = return_attendance(rollno, password)
    if isinstance(raw_data, str):
        return f"<h2>{raw_data}</h2>"

    attendance_data = data_json(raw_data)
    cgpa_data = return_cgpa(session)

    return render_template('dashboard.html',
                           rollno=rollno,
                           attendance=attendance_data,
                           cgpa=cgpa_data)

if __name__ == '__main__':
    app.run(debug=True)
