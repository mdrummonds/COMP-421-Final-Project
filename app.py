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
   
   # Create students table to store student information
   cursor.execute('''
       CREATE TABLE IF NOT EXISTS students (
           id INTEGER PRIMARY KEY AUTOINCREMENT,
           name TEXT NOT NULL,
           email TEXT NOT NULL UNIQUE,
           year INTEGER NOT NULL CHECK (year BETWEEN 1 AND 4)
       )
   ''')
    # Create courses table to store course information
   cursor.execute('''
       CREATE TABLE IF NOT EXISTS courses (
           id INTEGER PRIMARY KEY AUTOINCREMENT,
           name TEXT NOT NULL,
           instructor TEXT NOT NULL,
           available_seats INTEGER NOT NULL
       )
   ''')

    # Create enrollments table to track course enrollments
   cursor.execute('''
       CREATE TABLE IF NOT EXISTS enrollments (
           id INTEGER PRIMARY KEY AUTOINCREMENT,
           student_id INTEGER,
           course_id INTEGER,
           FOREIGN KEY (student_id) REFERENCES students (id),
           FOREIGN KEY (course_id) REFERENCES courses (id)
       )
   ''')
   
   # Created a trigger to decrement available seats when a student enrolls
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

# Displays homepage using HTML template
@app.route('/')
def home():
    return render_template('index.html')

# Route to register a sudent, validates inputs, and handles duplicate emails
@app.route('/register_student', methods=['POST'])
def register_student():
    # Retrieve student detail from form
    name = request.form['name']
    email = request.form['email']
    year = request.form['year']

    # Validate student name
    if not name.isalpha():
        return jsonify({'message': 'Name must only contain letters.'}), 400

    if len(name) < 2 or len(name) > 50:
        return jsonify({'message': 'Name must be between 2 and 50 characters.'}), 400

    # Validate year field
    try:
        year = int(year)
    except ValueError:
        return jsonify({'message': 'Year must be a valid number between 1 and 5.'}), 400

    # Validate year range
    if year < 1 or year > 4:
        return jsonify({'message': 'Year must be between 1 and 4.'}), 400


    # Add student to database
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


@app.route('/add_course', methods=['POST'])
def add_course():
   name = request.form['course_name']
   instructor = request.form['instructor']
   available_seats = request.form['available_seats']

   # Validate available seats
   try:
       available_seats = int(available_seats)
   except ValueError:
       return jsonify({'message': 'Available seats must be a valid number.'}), 400

   if available_seats < 0:
       return jsonify({'message': 'Available seats cannot be negative.'}), 400

   conn = sqlite3.connect('class_database.db')
   cursor = conn.cursor()

   try:
       cursor.execute('INSERT INTO courses (name, instructor, available_seats) VALUES (?, ?, ?)', 
                      (name, instructor, available_seats))
       conn.commit()
   except sqlite3.Error as e:
       conn.rollback()
       return jsonify({'message': f'Error adding course: {e}'}), 500
   finally:
       conn.close()

   return redirect(url_for('home'))


# Enrolls a student and updates seat count
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
        # Start the transaction
        conn.isolation_level = None  # This is to enable transactions
        cursor.execute('BEGIN TRANSACTION;')  # Explicitly start a transaction

        # Check if the student exists
        cursor.execute('SELECT id FROM students WHERE id = ?', (student_id,))
        student_exists = cursor.fetchone()
        if not student_exists:
            return jsonify({'message': 'Student not found.'}), 404

        # Check if the course has available seats
        cursor.execute('SELECT available_seats FROM courses WHERE id = ?', (course_id,))
        result = cursor.fetchone()

        if not result:
            return jsonify({'message': 'Course not found.'}), 404

        available_seats = result[0]

        if available_seats <= 0:
            return jsonify({'message': 'No available seats for this course.'}), 400

        # Check if the student is already enrolled in the course
        cursor.execute('SELECT * FROM enrollments WHERE student_id = ? AND course_id = ?', (student_id, course_id))
        already_enrolled = cursor.fetchone()
        if already_enrolled:
            return jsonify({'message': 'Student is already enrolled in this course.'}), 400

        # Insert the enrollment
        cursor.execute('INSERT INTO enrollments (student_id, course_id) VALUES (?, ?)', (student_id, course_id))


        # Commit the transaction
        conn.commit()

    except sqlite3.Error as e:
        # Rollback the transaction in case of an error
        conn.rollback()
        return jsonify({'message': f'Transaction failed: {e}'}), 500
    
    finally:
        conn.close()

    return jsonify({'message': 'Student enrolled successfully!'}), 200




#List courses for a student
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

    if year < 1 or year > 4:
        return jsonify({'message': 'Year must be between 1 and 4.'}), 400

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

   # Check if student ID exists 
   cursor.execute('SELECT 1 FROM students WHERE id = ?', (student_id,)) 
   student_exists = cursor.fetchone() 

   # Check if course ID exists 
   cursor.execute('SELECT 1 FROM courses WHERE id = ?', (course_id,)) 
   course_exists = cursor.fetchone()

   if not student_exists: 
        conn.close() 
        return jsonify({'message': 'Student ID does not exist'}), 400 
   if not course_exists: 
        conn.close() 
        return jsonify({'message': 'Course ID does not exist'}), 400
   
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
