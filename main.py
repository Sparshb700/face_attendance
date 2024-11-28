import mysql.connector as con
from datetime import date
import cv_code
from tabulate import tabulate
# Connect to the database
passwd = input("Input mysql password: ")
db = input("Name of mysql database: ")
my_con = con.connect(user="root", host="localhost", passwd=passwd, db=db)
cursor = my_con.cursor()

cursor.execute("show tables")
all_tables = [t[0] for t in cursor.fetchall()]
if "student" not in all_tables:
    cursor.execute("create table student (adm_no int primary key, name varchar(20))")
    my_con.commit()

def get_table_name(month=None, year=None):
    today = date.today()
    if not month:
        month = today.strftime("%b")
    if not year:
        year = today.strftime("%Y")
    return f"attendance_{month}_{year}"


def create_table_if_not_exists(table_name):
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            id INT AUTO_INCREMENT PRIMARY KEY,
            adm_no INT,
            name VARCHAR(255),
            date DATE,
            time TIME,
            status VARCHAR(20)
        )
    """)
    my_con.commit()


def get_date():
    today = date.today()
    return today.strftime("%Y-%m-%d")


def click_picture(adm_no, name_student):
    import cv2
    cam = cv2.VideoCapture(0)
    cv2.namedWindow("Press space to click picture")

    while True:
        ret, frame = cam.read()
        if not ret:
            break

        cv2.imshow("Press space to click picture", frame)

        k = cv2.waitKey(1)
        if k % 256 == 27:
            # ESC pressed
            print("Escape hit, closing...")
            break
        elif k % 256 == 32:
            # SPACE pressed
            img_name = f"{adm_no}_{name_student}.jpg"
            cv2.imwrite(f"image_attendance/{img_name}", frame)
            print("{} written!".format(img_name))

            cam.release()
            cv2.destroyAllWindows()
            break
    cam.release()
    cv2.destroyAllWindows()


def mark_attendance(date_today, table_name, update_all=False):
    recognized_students = cv_code.attendance()
    if update_all:
        cursor.execute(f"DELETE FROM {table_name} WHERE date = '{date_today}'")
        my_con.commit()
        print(f"Existing attendance for {date_today} deleted.")

    for data in recognized_students:
        values = data.split("_")
        adm_no = values[0]
        student_name = values[1]
        cursor.execute(f"""
            INSERT INTO {table_name} (adm_no, name, date, time, status)
            VALUES ({adm_no}, '{student_name}', '{date_today}', CURTIME(), 'Present')
        """)
        my_con.commit()
        print(f'Attendance marked for {student_name} on {date_today}')


def display_attendance(date_to_display, month=None, year=None):
    table_name = get_table_name(month, year)

    cursor.execute(f"""
        SELECT name, adm_no 
        FROM {table_name}
        WHERE date = '{date_to_display}'
    """)
    present_data = cursor.fetchall()
    present_adm_nos = [n[1] for n in present_data]

    cursor.execute('select name, adm_no from student')
    data = cursor.fetchall()
    table_data = [["Adm.no", "Name", "Status"]]

    if present_data:
        print(f"Attendance for {date_to_display}:")
        for entry in data:
            if entry[1] in present_adm_nos:
                table_data.append([entry[1], entry[0], "Present"])
            else:
                table_data.append([entry[1], entry[0], "Absent"])

        print(tabulate(table_data, headers="firstrow", tablefmt="fancy_grid"))

    else:
        print(f"No attendance records found or All Students were absent on {date_to_display}")


def add_student(name):
    cursor.execute("SELECT MAX(adm_no) FROM student")
    max_adm_no = cursor.fetchone()[0]
    new_adm_no = 1 if max_adm_no is None else max_adm_no + 1

    click_picture(new_adm_no, name)
    cursor.execute(f"INSERT INTO student (adm_no, name) VALUES ({new_adm_no}, '{name}')")
    my_con.commit()
    print(f"Added student {name} with Admission Number {new_adm_no} to database")


def remove_student(adm_no):
    table_name = get_table_name()

    cursor.execute(f"DELETE FROM {table_name} WHERE adm_no = {adm_no}")
    my_con.commit()

    cursor.execute(f"DELETE FROM student WHERE adm_no = {adm_no}")
    my_con.commit()
    print(f"Student with Admission Number {adm_no} removed from database")



def list_students():
    cursor.execute("SELECT adm_no, name FROM student")
    rows = cursor.fetchall()
    table_data = [["Name", "Adm.no"]]
    if rows:
        print("List of Students:")
        for row in rows:
            table_data.append([row[1], row[0]])
        print(tabulate(table_data, headers="firstrow", tablefmt="fancy_grid"))
    else:
        print("No students found in the database.")


while True:
    operation = int(input(
        "Which operation would you like to choose?\n1)Mark Attendance for today\n2)Show attendance for today\n3)Add Student\n4)Remove Student\n5)Update/Mark Attendance for a Specific Day\n6)Display Attendance for a Specific Day\n7)List All Students\n8)Exit\n>"))

    print("*****" * 10)
    if operation == 1:
        date_today = get_date()
        table_name = get_table_name()
        create_table_if_not_exists(table_name)

        cursor.execute(f"""
            SELECT * FROM {table_name}
            WHERE date = '{date_today}'
        """)
        existing_records = cursor.fetchall()

        if existing_records:
            overwrite = input(
                f"Attendance already exists for {date_today}. Do you want to overwrite it for all students? (yes/no): ").lower()
            if overwrite == 'yes':
                mark_attendance(date_today, table_name, update_all=True)
            else:
                print(f"Attendance for {date_today} was not changed.")
        else:
            mark_attendance(date_today, table_name)

    elif operation == 2:
        date_today = get_date()
        table_name = get_table_name()
        display_attendance(date_today)

    elif operation == 3:
        name = input("Enter the Student's Name: ")
        add_student(name)

    elif operation == 4:
        adm_no = int(input("Enter the Admission Number of the Student to Remove: "))
        remove_student(adm_no)

    elif operation == 5:
        month = input("Enter the month (e.g., Aug): ")
        year = input("Enter the year (e.g., 2024): ")
        date_to_update = input("Enter the date to update (YYYY-MM-DD): ")
        table_name = get_table_name(month, year)

        create_table_if_not_exists(table_name)

        cursor.execute(f"""
            SELECT DISTINCT name FROM {table_name}
            WHERE date = '{date_to_update}'
        """)
        existing_records = cursor.fetchall()

        if existing_records:
            update_all = input(
                f"Attendance records already exist for {date_to_update}. Do you want to update the entire day's record? (yes/no): ").lower()
            if update_all == "yes":
                mark_attendance(date_to_update, table_name, update_all=True)
            else:
                print(f"Attendance not changed for {date_to_update}")
        else:
            mark_attendance(date_to_update, table_name)

    elif operation == 6:
        month = input("Enter the month (e.g., Aug): ")
        year = input("Enter the year (e.g., 2024): ")
        date_to_display = input("Enter the date to display attendance (YYYY-MM-DD): ")
        display_attendance(date_to_display, month, year)

    elif operation == 7:
        list_students()

    elif operation == 8:
        break
    print("*****"*10)

cursor.close()
my_con.close()
