from flask import Flask, render_template, request, redirect, url_for, session
import os
import sqlite3

app = Flask(__name__)
app.secret_key = 'your-secret-key'
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Initialize DB
def init_db():
    conn = sqlite3.connect('products.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            description TEXT,
            price REAL,
            image TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# Admin credentials
ADMIN_USER = "admin"
ADMIN_PASS = "password"

# Routes
@app.route('/')
def index():
    conn = sqlite3.connect('products.db')
    products = conn.execute('SELECT * FROM products').fetchall()
    conn.close()
    return render_template('index.html', products=products)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form['username'] == ADMIN_USER and request.form['password'] == ADMIN_PASS:
            session['admin'] = True
            return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('admin', None)
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    if not session.get('admin'):
        return redirect(url_for('login'))
    conn = sqlite3.connect('products.db')
    products = conn.execute('SELECT * FROM products').fetchall()
    conn.close()
    return render_template('dashboard.html', products=products)

@app.route('/add', methods=['GET', 'POST'])
def add_product():
    if not session.get('admin'):
        return redirect(url_for('login'))
    if request.method == 'POST':
        title = request.form['title']
        desc = request.form['description']
        price = request.form['price']
        file = request.files['image']
        filename = file.filename
        path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(path)

        conn = sqlite3.connect('products.db')
        conn.execute('INSERT INTO products (title, description, price, image) VALUES (?, ?, ?, ?)',
                     (title, desc, price, filename))
        conn.commit()
        conn.close()
        return redirect(url_for('dashboard'))
    return render_template('add_product.html')

@app.route('/edit/<int:product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    if not session.get('admin'):
        return redirect(url_for('login'))

    conn = sqlite3.connect('products.db')
    if request.method == 'POST':
        title = request.form['title']
        desc = request.form['description']
        price = request.form['price']
        image = conn.execute('SELECT image FROM products WHERE id=?', (product_id,)).fetchone()[0]

        file = request.files['image']
        if file.filename:
            image = file.filename
            path = os.path.join(app.config['UPLOAD_FOLDER'], image)
            file.save(path)

        conn.execute('UPDATE products SET title=?, description=?, price=?, image=? WHERE id=?',
                     (title, desc, price, image, product_id))
        conn.commit()
        conn.close()
        return redirect(url_for('dashboard'))
    product = conn.execute('SELECT * FROM products WHERE id=?', (product_id,)).fetchone()
    conn.close()
    return render_template('edit_product.html', product=product)

@app.route('/delete/<int:product_id>')
def delete_product(product_id):
    if not session.get('admin'):
        return redirect(url_for('login'))
    conn = sqlite3.connect('products.db')
    conn.execute('DELETE FROM products WHERE id=?', (product_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    app.run(debug=True)
