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
            image TEXT,
            material TEXT,
            product_type TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

ADMIN_USER = "admin"
ADMIN_PASS = "password"

@app.route('/')
def index():
    conn = sqlite3.connect('products.db')
    conn.row_factory = sqlite3.Row

    # Get filters from query params
    selected_material = request.args.get('material')
    selected_type = request.args.get('product_type')
    sort_order = request.args.get('sort', 'asc')

    query = 'SELECT * FROM products WHERE 1=1'
    params = []

    if selected_material:
        query += ' AND material = ?'
        params.append(selected_material)
    if selected_type:
        query += ' AND product_type = ?'
        params.append(selected_type)

    if sort_order == 'desc':
        query += ' ORDER BY price DESC'
    else:
        query += ' ORDER BY price ASC'

    products = conn.execute(query, params).fetchall()

    # Fetch distinct materials and types for the filter dropdowns
    materials = [row[0] for row in conn.execute('SELECT DISTINCT material FROM products WHERE material IS NOT NULL')]
    product_types = [row[0] for row in conn.execute('SELECT DISTINCT product_type FROM products WHERE product_type IS NOT NULL')]

    conn.close()

    return render_template(
        'index.html',
        products=products,
        materials=materials,
        product_types=product_types
    )

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
        material = request.form['material']
        product_type = request.form['product_type']
        file = request.files['image']
        filename = file.filename
        path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(path)

        conn = sqlite3.connect('products.db')
        conn.execute('INSERT INTO products (title, description, price, image, material, product_type) VALUES (?, ?, ?, ?, ?, ?)',
                     (title, desc, price, filename, material, product_type))
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
        material = request.form['material']
        product_type = request.form['product_type']
        image = conn.execute('SELECT image FROM products WHERE id=?', (product_id,)).fetchone()[0]
        file = request.files['image']
        if file.filename:
            image = file.filename
            path = os.path.join(app.config['UPLOAD_FOLDER'], image)
            file.save(path)
        conn.execute('UPDATE products SET title=?, description=?, price=?, image=?, material=?, product_type=? WHERE id=?',
                     (title, desc, price, image, material, product_type, product_id))
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

@app.route('/product/<int:product_id>')
def product_detail(product_id):
    conn = sqlite3.connect('products.db')
    product = conn.execute('SELECT * FROM products WHERE id=?', (product_id,)).fetchone()
    conn.close()
    if not product:
        return "A termék nem található", 404
    return render_template('product_detail.html', product=product)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5003))
    app.run(host='0.0.0.0', port=port)
