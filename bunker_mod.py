
import math
import requests
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np

def gradeMap(grade):
    grade_map = {
        "O": 10, "A+": 9, "A": 8, "B+": 7, 
        "B": 6, "C+": 5, "C": 4, "RA": 0, "SA": 0, "W": 0
    }
    return grade_map.get(grade.strip().upper(), 0)

def return_attendance(username, pwd):
    try:
        session = requests.Session()
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

        # Login
        login_url = "https://ecampus.psgtech.ac.in/studzone2/"
        r = session.get(login_url, headers=headers)
        soup = BeautifulSoup(r.text, 'html.parser')

        viewstate = soup.select("#__VIEWSTATE")[0]["value"]
        eventvalidation = soup.select("#__EVENTVALIDATION")[0]["value"]
        viewstategen = soup.select("#__VIEWSTATEGENERATOR")[0]["value"]

        payload = {
            "__VIEWSTATE": viewstate,
            "__VIEWSTATEGENERATOR": viewstategen,
            "__EVENTVALIDATION": eventvalidation,
            "txtusercheck": username,
            "txtpwdcheck": pwd,
            "abcd3": "Login"
        }

        session.post(login_url, data=payload, headers=headers)

        # Get attendance
        attendance_url = "https://ecampus.psgtech.ac.in/studzone2/AttWfPercView.aspx"
        page = session.get(attendance_url, headers=headers)
        soup = BeautifulSoup(page.text, 'html.parser')

        table = soup.find("table", {"class": "cssbody"})
        if not table:
            return "Attendance data not available or invalid credentials"

        data = []
        for row in table.find_all("tr"):
            cols = [ele.text.strip() for ele in row.find_all("td")]
            data.append([ele for ele in cols if ele])

        return data, session

    except Exception as e:
        return f"Error: {str(e)}"

def data_json(data):
    response = []
    for item in data[1:]:
        if len(item) < 10:
            continue

        temp = {
            "name": item[0],
            "total_hours": int(item[1]),
            "exception_hour": int(item[2]),
            "total_present": int(item[4]),
            "percentage_of_attendance": float(item[5]),
            "attendance_from": item[8],
            "attendance_to": item[9],
            "type": "lab" if "lab" in item[0].lower() else "theory"
        }

        # Enhanced calculation with 75% minimum and exception hours
        total_eligible_hours = temp['total_hours'] + temp['exception_hour']
        required_for_75 = math.ceil(0.75 * total_eligible_hours)

        if temp['total_present'] < required_for_75:
            # Need to attend more classes
            temp['classes_to_attend'] = required_for_75 - temp['total_present']
            temp['classes_to_bunk'] = 0
            temp['status'] = 'must_attend'
        else:
            # Can bunk classes
            max_absent = math.floor(0.25 * total_eligible_hours)
            current_absent = total_eligible_hours - temp['total_present']
            temp['classes_to_bunk'] = max(0, max_absent - current_absent)
            temp['classes_to_attend'] = 0
            temp['status'] = 'can_bunk'

        # Add required percentage info
        temp['required_percentage'] = 75
        temp['shortage'] = max(0, required_for_75 - temp['total_present'])

        response.append(temp)
    return response

def return_cgpa(session):
    try:
        # Get results
        results_url = "https://ecampus.psgtech.ac.in/studzone2/FrmEpsStudResult.aspx"
        page = session.get(results_url)
        soup = BeautifulSoup(page.text, 'html.parser')

        table = soup.find("table", {"id": "DgResult"})
        if not table:
            return {"error": "No results found"}

        # Process results
        data = []
        semester_data = {}  # To store semester-wise data

        for row in table.find_all("tr")[1:]:  # Skip header
            cols = [ele.text.strip() for ele in row.find_all("td")]
            if len(cols) >= 6:  # Ensure valid row
                try:
                    credits = int(cols[3]) if cols[3].isdigit() else 0
                    semester = cols[0].strip()
                    grade = cols[4].split()[-1] if cols[4] else ""

                    course_data = {
                        "semester": semester,
                        "code": cols[1],
                        "title": cols[2],
                        "credits": credits,
                        "grade": grade,
                        "result": cols[5]
                    }
                    data.append(course_data)

                    # Group by semester for semester-wise CGPA calculation
                    if semester not in semester_data:
                        semester_data[semester] = []
                    semester_data[semester].append(course_data)

                except (ValueError, IndexError):
                    continue

        if not data:
            return {"error": "No valid course data found"}

        # Calculate overall CGPA
        total_points = 0
        total_credits = 0
        latest_sem = ""

        # Find the latest semester
        semester_numbers = []
        for semester in semester_data.keys():
            try:
                sem_num = convert_semester_to_number(semester)
                semester_numbers.append((sem_num, semester))
            except:
                semester_numbers.append((0, semester))

        if semester_numbers:
            semester_numbers.sort(reverse=True, key=lambda x: x[0])
            latest_sem = semester_numbers[0][1]

        # Calculate overall CGPA (cumulative across all semesters)
        for course in data:
            if (course["credits"] > 0 and 
                course["grade"] in ["O", "A+", "A", "B+", "B", "C+", "C"]):
                total_points += course["credits"] * gradeMap(course["grade"])
                total_credits += course["credits"]

        overall_cgpa = total_points / total_credits if total_credits > 0 else 0

        return {
            "latest_sem": latest_sem,
            "total_cgpa": round(overall_cgpa, 3),  # Changed from latest_sem_cgpa to total_cgpa
            "total_semesters": len(semester_data),
            "courses": data
        }

    except Exception as e:
        return {"error": str(e)}

def convert_semester_to_number(semester):
    """Convert semester string to number for comparison"""
    semester = semester.strip().upper()

    # Roman numeral conversion
    roman_map = {
        "I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6, "VII": 7, "VIII": 8,
        "IX": 9, "X": 10, "XI": 11, "XII": 12
    }

    if semester in roman_map:
        return roman_map[semester]

    # Try to extract number from string
    import re
    numbers = re.findall(r'\d+', semester)
    if numbers:
        return int(numbers[0])

    return 0

def get_timetable_data():
    """Sample timetable data - matches attendance subjects"""
    timetable = {
        "Monday": [
            {"time": "9:00-10:00", "subject": "Database Management Systems", "room": "CS201", "type": "Lecture"},
            {"time": "10:15-11:15", "subject": "Computer Networks", "room": "CS202", "type": "Lecture"},
            {"time": "11:30-12:30", "subject": "Software Engineering", "room": "CS203", "type": "Tutorial"},
            {"time": "1:30-3:30", "subject": "Database Management Systems Lab", "room": "CS Lab 1", "type": "Lab"},
        ],
        "Tuesday": [
            {"time": "9:00-10:00", "subject": "Web Technologies", "room": "CS301", "type": "Lecture"},
            {"time": "10:15-11:15", "subject": "Data Structures", "room": "CS302", "type": "Lecture"},
            {"time": "11:30-12:30", "subject": "Computer Networks", "room": "CS202", "type": "Tutorial"},
            {"time": "1:30-3:30", "subject": "Computer Networks Lab", "room": "CS Lab 2", "type": "Lab"},
        ],
        "Wednesday": [
            {"time": "9:00-10:00", "subject": "Software Engineering", "room": "CS203", "type": "Lecture"},
            {"time": "10:15-11:15", "subject": "Web Technologies", "room": "CS301", "type": "Tutorial"},
            {"time": "11:30-12:30", "subject": "Database Management Systems", "room": "CS201", "type": "Lecture"},
            {"time": "1:30-2:30", "subject": "Operating Systems", "room": "CS204", "type": "Lecture"},
        ],
        "Thursday": [
            {"time": "9:00-10:00", "subject": "Computer Networks", "room": "CS202", "type": "Lecture"},
            {"time": "10:15-11:15", "subject": "Software Engineering", "room": "CS203", "type": "Tutorial"},
            {"time": "11:30-12:30", "subject": "Web Technologies", "room": "CS301", "type": "Lecture"},
            {"time": "1:30-3:30", "subject": "Web Technologies Lab", "room": "CS Lab 3", "type": "Lab"},
        ],
        "Friday": [
            {"time": "9:00-10:00", "subject": "Data Structures", "room": "CS302", "type": "Lecture"},
            {"time": "10:15-11:15", "subject": "Operating Systems", "room": "CS204", "type": "Tutorial"},
            {"time": "11:30-12:30", "subject": "Database Management Systems", "room": "CS201", "type": "Tutorial"},
            {"time": "1:30-2:30", "subject": "Software Engineering", "room": "CS203", "type": "Lecture"},
        ]
    }
    return timetable
