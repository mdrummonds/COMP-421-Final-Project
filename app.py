from flask import Flask, request, jsonify
import sqlite3

app = Flask(__name__)

def init_db():
    conn = sqlite3.connect('class_database.db')
    cursor = conn.cursor()

    # Students table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            major TEXT NOT NULL
        )
    ''')

    # Courses table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            instructor TEXT NOT NULL,
            available_seats INTEGER NOT NULL
        )
    ''')

    # Enrollments table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS enrollments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            course_id INTEGER,
            FOREIGN KEY (student_id) REFERENCES students (id),
            FOREIGN KEY (course_id) REFERENCES courses (id)
        )
    ''')

    conn.commit()
    conn.close()

@app.route('/')
def home():
    return 'Welcome to the Student Course Registration System!'

@app.route('/register_student', methods=['POST'])
def register_student():
    data = request.get_json()
    name = data['name']
    email = data['email']
    major = data['major']

    conn = sqlite3.connect('class_database.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO students (name, email, major) VALUES (?, ?, ?)', (name, email, major))
    conn.commit()
    conn.close()

    return jsonify({'message': 'Student registered successfully!'})

@app.route('/add_course', methods=['POST'])
def add_course():
    data = request.get_json()
    name = data['name']
    instructor = data['instructor']
    available_seats = data['available_seats']

    conn = sqlite3.connect('class_database.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO courses (name, instructor, available_seats) VALUES (?, ?, ?)', (name, instructor, available_seats))
    conn.commit()
    conn.close()

    return jsonify({'message': 'Course added successfully!'})

@app.route('/enroll', methods=['POST'])
def enroll():
    data = request.get_json()
    student_id = data['student_id']
    course_id = data['course_id']

    conn = sqlite3.connect('class_database.db')
    cursor = conn.cursor()

    cursor.execute('SELECT available_seats FROM courses WHERE id = ?', (course_id,))
    available_seats = cursor.fetchone()[0]
    
    if available_seats > 0:
        cursor.execute('INSERT INTO enrollments (student_id, course_id) VALUES (?, ?)', (student_id, course_id))
        cursor.execute('UPDATE courses SET available_seats = available_seats - 1 WHERE id = ?', (course_id,))
        conn.commit()
        message = 'Student enrolled successfully!'
    else:
        message = 'No available seats for this course.'

    conn.close()
    return jsonify({'message': message})

@app.route('/view_enrollments/<int:student_id>', methods=['GET'])
def view_enrollments(student_id):
    conn = sqlite3.connect('class_database.db')
    cursor = conn.cursor()

    cursor.execute('''
        SELECT courses.name, courses.instructor FROM enrollments
        JOIN courses ON enrollments.course_id = courses.id
        WHERE enrollments.student_id = ?
    ''', (student_id,))
    courses = cursor.fetchall()

    conn.close()
    return jsonify({'enrolled_courses': courses})

@app.route('/drop_course', methods=['POST'])
def drop_course():
    data = request.get_json()
    student_id = data['student_id']
   


if __name__ == '__main__':
    init_db()
    app.run(port=5000)
