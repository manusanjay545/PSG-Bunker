import math
import requests
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np

def _extract_name_from_soup(soup):
    """Helper to find the student name in a BeautifulSoup parsed page"""
    # Try common label/span IDs where name appears
    for label_id in ["lblWelcomeStudName", "lblName", "lblStudentName",
                     "lblWelcome", "lblStudName", "lblstudname",
                     "Label1", "lbl_StuName", "lbl_stuname"]:
        elem = soup.find(id=label_id)
        if elem and elem.get_text(strip=True):
            name = elem.get_text(strip=True)
            # Clean up "Welcome, Name" patterns
            if "welcome" in name.lower():
                name = name.split(",", 1)[-1].strip().rstrip("!").strip()
            if name and len(name) > 1 and not name.replace(" ", "").isdigit():
                return name

    # Search all spans, labels, divs for welcome text with name
    for tag in soup.find_all(["span", "label", "div", "td"]):
        text = tag.get_text(strip=True)
        if not text:
            continue
        text_lower = text.lower()
        if "welcome" in text_lower and len(text) > 8 and len(text) < 100:
            if "," in text:
                name = text.split(",", 1)[1].strip().rstrip("!").strip()
            else:
                for prefix in ["Welcome ", "welcome ", "WELCOME "]:
                    if text.startswith(prefix):
                        name = text[len(prefix):].strip().rstrip("!").strip()
                        break
                else:
                    continue
            if name and len(name) > 1 and not name.replace(" ", "").isdigit():
                return name
    return None

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

        login_response = session.post(login_url, data=payload, headers=headers)

        # Check if login failed (page still shows login form means invalid password)
        login_soup = BeautifulSoup(login_response.text, 'html.parser')
        login_error = login_soup.find("span", {"id": "lblStatus"})
        # If login form fields are still present, login failed
        if login_soup.find("input", {"name": "txtusercheck"}) and login_soup.find("input", {"name": "txtpwdcheck"}):
            return "Invalid Password"

        # Try to extract student name from post-login page
        student_name = _extract_name_from_soup(login_soup)

        # Get attendance
        attendance_url = "https://ecampus.psgtech.ac.in/studzone2/AttWfPercView.aspx"
        page = session.get(attendance_url, headers=headers)
        soup = BeautifulSoup(page.text, 'html.parser')

        # Also try extracting name from attendance page if not found yet
        if not student_name:
            student_name = _extract_name_from_soup(soup)

        table = soup.find("table", {"class": "cssbody"})
        if not table:
            # Login succeeded but attendance data is not available
            return [], session, student_name

        data = []
        for row in table.find_all("tr"):
            cols = [ele.text.strip() for ele in row.find_all("td")]
            data.append([ele for ele in cols if ele])

        return data, session, student_name

    except Exception as e:
        return f"Error: {str(e)}"

def get_course_plan(session):
    """Get course plan with course titles"""
    try:
        course_url = "https://ecampus.psgtech.ac.in/studzone2/AttWfStudTimtab.aspx"
        page = session.get(course_url)
        soup = BeautifulSoup(page.text, 'html.parser')

        table = soup.find("table", {"id": "TbCourDesc"})
        if not table:
            return {}

        course_mapping = {}
        for row in table.find_all("tr")[1:]:  # Skip header
            cols = [ele.text.strip() for ele in row.find_all("td")]
            if len(cols) >= 2:
                course_mapping[cols[0]] = cols[1]

        return course_mapping
    except:
        return {}

def get_student_name(session):
    """Get student name from the eCampus portal"""
    try:
        # Try multiple pages where the name might appear
        urls = [
            "https://ecampus.psgtech.ac.in/studzone2/",
            "https://ecampus.psgtech.ac.in/studzone2/CAaborali498.aspx",
            "https://ecampus.psgtech.ac.in/studzone2/AttWfPercView.aspx",
            "https://ecampus.psgtech.ac.in/studzone2/AttWfStudTimtab.aspx",
        ]

        for url in urls:
            try:
                page = session.get(url, timeout=5)
                soup = BeautifulSoup(page.text, 'html.parser')

                # Try common label/span IDs where name appears
                for label_id in ["lblWelcomeStudName", "lblName", "lblStudentName",
                                 "lblWelcome", "lblStudName", "lblstudname",
                                 "Label1", "lbl_StuName", "lbl_stuname"]:
                    elem = soup.find(id=label_id)
                    if elem and elem.get_text(strip=True):
                        name = elem.get_text(strip=True)
                        # Clean up "Welcome, Name" patterns
                        if "welcome" in name.lower():
                            name = name.split(",", 1)[-1].strip().rstrip("!").strip()
                        if name and len(name) > 1 and not name.replace(" ", "").isdigit():
                            return name

                # Search all spans, labels, divs for welcome text with name
                for tag in soup.find_all(["span", "label", "div", "td"]):
                    text = tag.get_text(strip=True)
                    if not text:
                        continue
                    text_lower = text.lower()
                    # Look for "Welcome, Name" or "Welcome Name" patterns
                    if "welcome" in text_lower and len(text) > 8 and len(text) < 100:
                        # Try splitting by comma
                        if "," in text:
                            name = text.split(",", 1)[1].strip().rstrip("!").strip()
                        else:
                            # Try removing "Welcome" prefix
                            for prefix in ["Welcome ", "welcome ", "WELCOME "]:
                                if text.startswith(prefix):
                                    name = text[len(prefix):].strip().rstrip("!").strip()
                                    break
                            else:
                                continue
                        if name and len(name) > 1 and not name.replace(" ", "").isdigit():
                            return name

            except:
                continue

        return None
    except:
        return None

def get_timetable(session):
    """Get full weekly timetable from the timetable page"""
    try:
        timetable_url = "https://ecampus.psgtech.ac.in/studzone2/AttWfStudTimtab.aspx"
        page = session.get(timetable_url)
        soup = BeautifulSoup(page.text, 'html.parser')

        # Try to find the timetable grid table (usually has id like TbTimtab or similar)
        timetable_table = None
        # Look for tables that contain day names (Mon, Tue, etc.)
        for table in soup.find_all("table"):
            table_text = table.get_text()
            if any(day in table_text for day in ["MON", "TUE", "WED", "THU", "FRI", "Mon", "Tue", "Wed", "Thu", "Fri"]):
                # Skip the course description table
                if table.get("id") == "TbCourDesc":
                    continue
                timetable_table = table
                break

        if not timetable_table:
            return {"headers": [], "rows": []}

        # Extract headers and rows
        headers = []
        rows = []
        all_rows = timetable_table.find_all("tr")

        for i, row in enumerate(all_rows):
            cells = row.find_all(["th", "td"])
            cell_texts = [cell.get_text(strip=True) for cell in cells]

            if not any(cell_texts):  # Skip empty rows
                continue

            # Skip rows that are just a single number (stray row counts from HTML)
            if len(cell_texts) == 1 and cell_texts[0].isdigit():
                continue

            # Skip rows with very few cells compared to expected timetable width
            if headers and len(cell_texts) < 2:
                continue

            if i == 0 or (not headers and cell_texts):
                headers = cell_texts
            else:
                if any(cell_texts):  # Only add non-empty rows
                    # Ensure row has the same number of columns as headers
                    if headers and len(cell_texts) != len(headers):
                        # Pad or trim to match header length
                        while len(cell_texts) < len(headers):
                            cell_texts.append("")
                        cell_texts = cell_texts[:len(headers)]
                    rows.append(cell_texts)

        return {"headers": headers, "rows": rows}
    except:
        return {"headers": [], "rows": []}

def data_json(data, course_plan=None):
    response = []
    for item in data[1:]:
        if len(item) < 10:
            continue

        temp = {
            "name": item[0],
            "course_title": course_plan.get(item[0], item[0]) if course_plan else item[0],
            "total_hours": int(item[1]),
            "exception_hour": int(item[2]),
            "total_present": int(item[4]),
            "percentage_of_attendance": float(item[5]),
            "attendance_from": item[8],
            "attendance_to": item[9]
        }

        if temp['percentage_of_attendance'] < 75:
            temp['class_to_attend'] = math.ceil(
                (0.75 * temp['total_hours'] - temp['total_present']) / 0.25
            )
        else:
            temp['class_to_bunk'] = math.floor(
                (temp['total_present'] - 0.75 * temp['total_hours']) / 0.75
            )

        response.append(temp)
    return response

