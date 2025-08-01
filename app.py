from flask import Flask, render_template, request
from bunker_mod import return_attendance, data_json, return_cgpa

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login', methods=['POST'])
def login():
    rollno = request.form['rollno']
    password = request.form['password']

    result = return_attendance(rollno, password)
    if isinstance(result, str):
        return render_template("index.html", error=result)

    attendance_raw, session = result
    attendance_data = data_json(attendance_raw)
    cgpa_data = return_cgpa(session)

    return render_template("dashboard.html",
                           rollno=rollno,
                           attendance=attendance_data,
                           cgpa=cgpa_data)
    
@app.route('/robots.txt')
def robots():
    return app.send_static_file('robots.txt')

@app.route('/sitemap.xml')
def sitemap():
    return app.send_static_file('sitemap.xml')

@app.route("/calendar")
def calendar_page():
    return render_template("calendar.html")

from flask import send_from_directory

@app.route('/logo.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'logo.ico', mimetype='image/vnd.microsoft.icon')

    

    

if __name__ == '__main__':
    app.run(debug=True)
