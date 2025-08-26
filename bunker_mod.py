import math
import requests
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
import re

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

        # Login to PSG eCampus
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

        # Get attendance data
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

def get_course_plan(session):
    """Fetch real course details from courseplan page with enhanced parsing"""
    try:
        courseplan_url = "https://ecampus.psgtech.ac.in/studzone/Attendance/courseplan"
        page = session.get(courseplan_url)
        soup = BeautifulSoup(page.text, 'html.parser')

        courses = {}

        # Parse course data from the page - try multiple table structures
        tables = soup.find_all("table")

        for table in tables:
            rows = table.find_all("tr")

            # Skip if table has less than 2 rows (header + data)
            if len(rows) < 2:
                continue

            for i, row in enumerate(rows):
                # Skip header rows
                if i == 0:
                    continue

                cols = row.find_all(["td", "th"])

                if len(cols) >= 2:
                    # Try different column arrangements
                    # Format 1: Code | Name | Credits
                    if len(cols) >= 3:
                        course_code = cols[0].text.strip()
                        course_name = cols[1].text.strip()
                        credits = cols[2].text.strip() if len(cols) > 2 else ""
                    # Format 2: Code | Name  
                    else:
                        course_code = cols[0].text.strip()
                        course_name = cols[1].text.strip()
                        credits = ""

                    # Clean and validate data
                    if course_code and course_name and len(course_code) > 0 and len(course_name) > 2:
                        # Remove extra whitespace and clean up
                        course_code = re.sub(r'\s+', ' ', course_code).strip()
                        course_name = re.sub(r'\s+', ' ', course_name).strip()

                        # Store with multiple keys for better matching
                        key = course_code.upper()
                        courses[key] = {
                            'name': course_name,
                            'credits': credits,
                            'code': course_code
                        }

                        # Also store partial matches
                        # Extract just the alphanumeric code part
                        code_clean = re.sub(r'[^A-Z0-9]', '', course_code.upper())
                        if code_clean and code_clean != key:
                            courses[code_clean] = courses[key]

        print(f"Fetched {len(courses)} courses from courseplan")
        return courses

    except Exception as e:
        print(f"Error fetching course plan: {e}")
        return {}

def find_course_name(subject_text, course_map):
    """Enhanced course name matching with multiple strategies"""
    if not course_map:
        return subject_text

    original = subject_text.strip()

    # Strategy 1: Direct lookup
    if original.upper() in course_map:
        return course_map[original.upper()]['name']

    # Strategy 2: Extract course code patterns
    # Look for patterns like CS8491, IT8501, etc.
    code_patterns = re.findall(r'[A-Z]{2,3}\d{4}', original.upper())
    for pattern in code_patterns:
        if pattern in course_map:
            return course_map[pattern]['name']

    # Strategy 3: Look for any alphanumeric code
    code_clean = re.sub(r'[^A-Z0-9]', '', original.upper())
    if code_clean in course_map:
        return course_map[code_clean]['name']

    # Strategy 4: Partial matching - find code within the text
    for code, course_info in course_map.items():
        if code in original.upper() or any(word in code for word in original.upper().split() if len(word) > 2):
            return course_info['name']

    # Strategy 5: Reverse lookup - check if subject name matches any stored course name
    original_words = set(original.upper().split())
    for code, course_info in course_map.items():
        course_words = set(course_info['name'].upper().split())
        # If significant overlap in words, it might be the same course
        if len(original_words.intersection(course_words)) >= min(2, len(original_words)):
            return course_info['name']

    # If no match found, return original
    return original

def data_json(data, course_map=None):
    response = []
    for item in data[1:]:
        if len(item) < 10:
            continue

        # Get enhanced course name from course map
        original_name = item[0]
        course_name = find_course_name(original_name, course_map) if course_map else original_name

        temp = {
            "name": course_name,  # Full course name from courseplan
            "full_course_name": course_name,  # Explicit field for frontend
            "original_name": original_name,  # Keep original for reference
            "total_hours": int(item[1]),
            "exception_hour": int(item[2]),
            "total_present": int(item[4]),
            "percentage_of_attendance": float(item[5]),
            "attendance_from": item[8],
            "attendance_to": item[9],
            "type": "lab" if "lab" in original_name.lower() else "theory"
        }

        # Calculate attendance requirements
        total_eligible_hours = temp['total_hours'] + temp['exception_hour']
        required_for_75 = math.ceil(0.75 * total_eligible_hours)

        if temp['total_present'] < required_for_75:
            temp['classes_to_attend'] = required_for_75 - temp['total_present']
            temp['classes_to_bunk'] = 0
            temp['status'] = 'must_attend'
        else:
            max_absent = math.floor(0.25 * total_eligible_hours)
            current_absent = total_eligible_hours - temp['total_present']
            temp['classes_to_bunk'] = max(0, max_absent - current_absent)
            temp['classes_to_attend'] = 0
            temp['status'] = 'can_bunk'

        temp['required_percentage'] = 75
        temp['shortage'] = max(0, required_for_75 - temp['total_present'])

        response.append(temp)
    return response

def return_cgpa(session):
    try:
        results_url = "https://ecampus.psgtech.ac.in/studzone2/FrmEpsStudResult.aspx"
        page = session.get(results_url)
        soup = BeautifulSoup(page.text, 'html.parser')

        table = soup.find("table", {"id": "DgResult"})
        if not table:
            return {"error": "No results found"}

        data = []
        semester_data = {}

        for row in table.find_all("tr")[1:]:
            cols = [ele.text.strip() for ele in row.find_all("td")]
            if len(cols) >= 6:
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

                    if semester not in semester_data:
                        semester_data[semester] = []
                    semester_data[semester].append(course_data)

                except (ValueError, IndexError):
                    continue

        if not data:
            return {"error": "No valid course data found"}

        # Calculate CGPA
        total_points = 0
        total_credits = 0
        latest_sem = ""

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

        for course in data:
            if (course["credits"] > 0 and 
                course["grade"] in ["O", "A+", "A", "B+", "B", "C+", "C"]):
                total_points += course["credits"] * gradeMap(course["grade"])
                total_credits += course["credits"]

        overall_cgpa = total_points / total_credits if total_credits > 0 else 0

        return {
            "latest_sem": latest_sem,
            "total_cgpa": round(overall_cgpa, 3),
            "total_semesters": len(semester_data),
            "courses": data
        }

    except Exception as e:
        return {"error": str(e)}

def convert_semester_to_number(semester):
    semester = semester.strip().upper()
    roman_map = {
        "I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6, "VII": 7, "VIII": 8,
        "IX": 9, "X": 10, "XI": 11, "XII": 12
    }

    if semester in roman_map:
        return roman_map[semester]

    numbers = re.findall(r'\d+', semester)
    if numbers:
        return int(numbers[0])

    return 0
