from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3
from functools import wraps

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'
app.config['SESSION_TYPE'] = 'filesystem'

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Initialize database
def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    # Create users table
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )
    ''')

    # Create items table linked to users
    c.execute('''
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            type TEXT NOT NULL,
            title TEXT NOT NULL,
            genre TEXT NOT NULL,
            status TEXT NOT NULL,
            rating INTEGER,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    conn.commit()
    conn.close()

init_db()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if not username or not password:
            flash('Please fill all fields.')
            return redirect(url_for('signup'))

        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute('SELECT * FROM users WHERE username = ?', (username,))
        existing_user = c.fetchone()

        if existing_user:
            conn.close()
            flash('Username already taken. Please choose another.')
            return redirect(url_for('signup'))

        c.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password))
        conn.commit()
        conn.close()
        flash('Account created! You can now log in.')
        return redirect(url_for('login'))

    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, password))
        user = c.fetchone()
        conn.close()

        if user:
            session['user'] = username
            session['user_id'] = user[0]
            flash('Logged in successfully!')
            return redirect(url_for('home'))
        else:
            flash('Invalid credentials. Please try again.')
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    session.pop('user_id', None)
    flash('Logged out successfully!')
    return redirect(url_for('login'))

@app.route('/add', methods=['GET', 'POST'])
@login_required
def add_item():
    if request.method == 'POST':
        type = request.form.get('type')
        title = request.form.get('title')
        genre = request.form.get('genre')
        status = request.form.get('status')
        rating = request.form.get('rating')

        if not (type and title and genre and status):
            flash('Please fill all required fields.')
            return redirect(url_for('add_item'))

        if rating == '':
            rating = None

        user_id = session.get('user_id')

        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute('''
            INSERT INTO items (user_id, type, title, genre, status, rating)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, type, title, genre, status, rating))
        conn.commit()
        conn.close()
        flash('Entry added successfully!')
        return redirect(url_for('view_items'))

    return render_template('add.html')


@app.route('/view')
@login_required
def view_items():
    query = request.args.get('q', '').strip()
    user_id = session.get('user_id')

    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    if query:
        search_term = f"%{query}%"
        c.execute('''
            SELECT * FROM items
            WHERE user_id = ? AND (title LIKE ? OR type LIKE ? OR genre LIKE ?)
            ORDER BY id DESC
        ''', (user_id, search_term, search_term, search_term))
    else:
        c.execute('SELECT * FROM items WHERE user_id = ? ORDER BY id DESC', (user_id,))

    items = c.fetchall()
    conn.close()
    return render_template('view.html', items=items)

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_item(id):
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    if request.method == 'POST':
        type = request.form.get('type')
        title = request.form.get('title')
        genre = request.form.get('genre')
        status = request.form.get('status')
        rating = request.form.get('rating')
        if rating == '':
            rating = None

        c.execute('''
            UPDATE items
            SET type = ?, title = ?, genre = ?, status = ?, rating = ?
            WHERE id = ?
        ''', (type, title, genre, status, rating, id))
        conn.commit()
        conn.close()
        flash('Entry updated successfully!')
        return redirect(url_for('view_items'))

    c.execute('SELECT * FROM items WHERE id = ?', (id,))
    item = c.fetchone()
    conn.close()
    return render_template('edit.html', item=item)

@app.route('/delete/<int:id>')
@login_required
def delete_item(id):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('DELETE FROM items WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    flash('Entry deleted successfully!')
    return redirect(url_for('view_items'))

if __name__ == '__main__':
    app.run(debug=True)

from waitress import serve

if __name__ == '__main__':
    serve(app, host='0.0.0.0', port=8080)
