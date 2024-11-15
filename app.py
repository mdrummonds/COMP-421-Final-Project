from flask import Flask
import sqlite3

app = Flask(__name__)

def init_db():
   conn = sqlite3.connect('class_database.db')
   cursor = conn.cursor()
   
   cursor.execute('''
       CREATE TABLE IF NOT EXISTS students (
           id INTEGER PRIMARY KEY AUTOINCREMENT,
           name TEXT NOT NULL,
           grade TEXT NOT NULL
       )
   ''')
   
   conn.commit()
   conn.close()

@app.route('/')
def home():
   return 'Hello, World!'

if __name__ == '__main__':
   init_db()
   app.run(port=5000)  # Default port is 5000, but you can change this if you want