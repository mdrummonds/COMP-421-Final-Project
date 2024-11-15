from flask import Flask, request, jsonify, render_template, redirect, url_for
import sqlite3

app = Flask(__name__)

def init_db():
   conn = sqlite3.connect('class_database.db')
   cursor = conn.cursor()

   # Create tables if they don't exist
   cursor.execute('''
       CREATE TABLE IF NOT EXISTS students (
           id INTEGER PRIMARY KEY AUTOINCREMENT,
           name TEXT NOT NULL,
           email TEXT NOT NULL,
           major TEXT NOT NULL
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
   major = request.form['major']

   conn = sqlite3.connect('class_database.db')
   cursor = conn.cursor()
   cursor.execute('INSERT INTO students (name, email, major) VALUES (?, ?, ?)', (name, email, major))
   conn.commit()
   conn.close()

   return redirect(url_for('home'))

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
   student_id = request.form['student_id']
   course_id = request.form['course_id']

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

if __name__ == '__main__':
   init_db()
   app.run(port=5000, debug=True)