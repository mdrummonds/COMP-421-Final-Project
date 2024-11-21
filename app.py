from flask import Flask, request, jsonify, render_template, redirect, url_for
import sqlite3

app = Flask(__name__)

def init_db():
   conn = sqlite3.connect('class_database.db')
   cursor = conn.cursor()
    # Drop tables for development (remove in production)
   cursor.execute('DROP TABLE IF EXISTS students')
   cursor.execute('DROP TABLE IF EXISTS courses')
   cursor.execute('DROP TABLE IF EXISTS enrollments')
   
   # Create tables if they don't exist
   cursor.execute('''
       CREATE TABLE IF NOT EXISTS students (
           id INTEGER PRIMARY KEY AUTOINCREMENT,
           name TEXT NOT NULL,
           email TEXT NOT NULL UNIQUE,
           year INTEGER NOT NULL CHECK (year BETWEEN 1 AND 5)
       )
   ''')

   cursor.execute('''
       CREATE TABLE IF NOT EXISTS courses (
           id INTEGER PRIMARY KEY AUTOINCREMENT,
           name TEXT NOT NULL,
           instructor TEXT NOT NULL,
           available_seats INTEGER NOT NULL
       )
   ''')

   cursor.execute('''
       CREATE TABLE IF NOT EXISTS enrollments (
           id INTEGER PRIMARY KEY AUTOINCREMENT,
           student_id INTEGER,
           course_id INTEGER,
           FOREIGN KEY (student_id) REFERENCES students (id),
           FOREIGN KEY (course_id) REFERENCES courses (id)
       )
   ''')
   
   # Created a trigger to automatically update the available seats for a course whenever a student enrolls in that course.
   cursor.execute('''
        CREATE TRIGGER IF NOT EXISTS update_seats_after_enrollment
        AFTER INSERT ON enrollments
        FOR EACH ROW
        BEGIN
            UPDATE courses
            SET available_seats = available_seats - 1
            WHERE id = NEW.course_id;
        END;
    ''')

   conn.commit()
   conn.close()

# Route for the main page
@app.route('/')
def home():
    return render_template('index.html')

# Route to register a student
@app.route('/register_student', methods=['POST'])
def register_student():
    name = request.form['name']
    email = request.form['email']
    year = request.form['year']

    # Convert year to an integer and handle potential conversion errors
    try:
        year = int(year)
    except ValueError:
        return jsonify({'message': 'Year must be a valid number between 1 and 5.'}), 400

    # Validate year range
    if year < 1 or year > 5:
        return jsonify({'message': 'Year must be between 1 and 5.'}), 400

    conn = sqlite3.connect('class_database.db')
    cursor = conn.cursor()

    try:
        cursor.execute('INSERT INTO students (name, email, year) VALUES (?, ?, ?)', (name, email, year))
        student_id = cursor.lastrowid
        conn.commit()
    except sqlite3.IntegrityError:
        # Handle duplicate email issue
        conn.close()
        return jsonify({'message': 'Email already exists. Please use a different email.'}), 400

    conn.close()
    return jsonify({'message': f'Student added successfully with ID: {student_id}'}), 200


# Route to add a course
@app.route('/add_course', methods=['POST'])
def add_course():
   name = request.form['course_name']
   instructor = request.form['instructor']
   available_seats = request.form['available_seats']

   conn = sqlite3.connect('class_database.db')
   cursor = conn.cursor()
   cursor.execute('INSERT INTO courses (name, instructor, available_seats) VALUES (?, ?, ?)', (name, instructor, available_seats))
   conn.commit()
   conn.close()

   return redirect(url_for('home'))

# Other endpoints like /enroll, /drop_course, etc. will follow a similar format
# For example:
@app.route('/enroll', methods=['POST'])
def enroll():
    student_id = request.form.get('student_id')
    course_id = request.form.get('course_id')

    # Validate input
    if not student_id or not course_id:
        return jsonify({'message': 'Student ID and Course ID are required.'}), 400

    conn = sqlite3.connect('class_database.db')
    cursor = conn.cursor()

    try:
        # Check if the course has available seats
        cursor.execute('SELECT available_seats FROM courses WHERE id = ?', (course_id,))
        result = cursor.fetchone()

        if not result:
            return jsonify({'message': 'Course not found.'}), 404

        available_seats = result[0]

        if available_seats <= 0:
            return jsonify({'message': 'No available seats for this course.'}), 400

        # Insert the enrollment record
        cursor.execute('INSERT INTO enrollments (student_id, course_id) VALUES (?, ?)', (student_id, course_id))
        conn.commit()

    except sqlite3.IntegrityError:
        return jsonify({'message': 'Enrollment already exists or invalid student ID.'}), 400

    finally:
        conn.close()

    return jsonify({'message': 'Student enrolled successfully!'}), 200



@app.route('/student_courses/<int:student_id>', methods=['GET'])
def student_courses(student_id):
   conn = sqlite3.connect('class_database.db')
   cursor = conn.cursor()
   
   # Join query to fetch student email, course name, and instructor
   cursor.execute('''
       SELECT students.name, students.email, courses.name AS course_name, courses.instructor 
       FROM enrollments
       JOIN students ON enrollments.student_id = students.id
       JOIN courses ON enrollments.course_id = courses.id
       WHERE students.id = ?
   ''', (student_id,))
   
   courses = cursor.fetchall()
   conn.close()

   # Formatting response as JSON
   if courses:
       student_info = {'name': courses[0][0], 'email': courses[0][1], 'courses': []}
       for course in courses:
           student_info['courses'].append({'course_name': course[2], 'instructor': course[3]})
       return jsonify(student_info)
   else:
       return jsonify({'message': 'No courses found for this student.'}), 404

@app.route('/courses', methods=['GET'])
def get_courses():
   conn = sqlite3.connect('class_database.db')
   cursor = conn.cursor()
   
   # Query to fetch all courses with their details
   cursor.execute('SELECT id, name, instructor, available_seats FROM courses')
   courses = cursor.fetchall()
   conn.close()

   # Format courses as JSON
   courses_list = [
       {'id': course[0], 'name': course[1], 'instructor': course[2], 'available_seats': course[3]}
       for course in courses
   ]
   return jsonify(courses_list)

@app.route('/update_student/<int:student_id>', methods=['POST'])
def update_student(student_id):
    name = request.form['name']
    email = request.form['email']
    year = request.form['year']

    # Validate and process year
    try:
        year = int(year)
    except ValueError:
        return jsonify({'message': 'Year must be a valid number between 1 and 5.'}), 400

    if year < 1 or year > 5:
        return jsonify({'message': 'Year must be between 1 and 5.'}), 400

    conn = sqlite3.connect('class_database.db')
    cursor = conn.cursor()

    try:
        # Update student information (excluding ID)
        cursor.execute('''
            UPDATE students
            SET name = ?, email = ?, year = ?
            WHERE id = ?
        ''', (name, email, year, student_id))
        conn.commit()

        if cursor.rowcount == 0:
            conn.close()
            return jsonify({'message': 'Student not found.'}), 404

    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({'message': 'Email already exists. Please use a different email.'}), 400

    conn.close()
    return jsonify({'message': 'Student information updated successfully!'}), 200


@app.route('/unenroll', methods=['POST'])
def unenroll():
   student_id = request.form['student_id']
   course_id = request.form['course_id']

   conn = sqlite3.connect('class_database.db')
   cursor = conn.cursor()
   
   # Delete student id from a course
   cursor.execute('DELETE FROM enrollments WHERE student_id = ? AND course_id = ?', (student_id, course_id))

   # Check if unenrollment successful
   if cursor.rowcount > 0:
        # Update available seats
        cursor.execute('UPDATE courses SET available_seats = available_seats + 1 WHERE id = ?', (course_id,))
        message = 'Student successfully unenrolled from the course.'
   else:
        # Unenrollment was unsuccessful
        message = 'Student successfully unenrolled from the course.'

   conn.commit()
   conn.close()
   return jsonify({'message': message})
 

if __name__ == '__main__':
   init_db()
   app.run(port=5000, debug=True)
