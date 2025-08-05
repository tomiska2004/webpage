from flask import Flask, render_template, request, redirect, url_for, session
import os
import sqlite3
from werkzeug.utils import secure_filename

from flask_babel import Babel, gettext as _
from flask import request

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Babel config
app.config['BABEL_DEFAULT_LOCALE'] = 'hu'
app.config['BABEL_SUPPORTED_LOCALES'] = ['en', 'hu', 'ro']
app.config['BABEL_TRANSLATION_DIRECTORIES'] = 'translations'

# Define selector function
def get_locale():
    # Example: allow override via ?lang=en in URL
    lang = request.args.get('lang')
    if lang in app.config['BABEL_SUPPORTED_LOCALES']:
        session['lang'] = lang
    return session.get('lang', app.config['BABEL_DEFAULT_LOCALE'])

# Pass selector to Babel
babel = Babel(app, locale_selector=get_locale)
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Helper to connect DB
def get_db_connection():
    conn = sqlite3.connect('products.db')
    conn.row_factory = sqlite3.Row
    return conn

# Initialize DB
def init_db():
    conn = get_db_connection()
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
    c.execute('''
        CREATE TABLE IF NOT EXISTS product_images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER,
            filename TEXT,
            FOREIGN KEY(product_id) REFERENCES products(id)
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# Admin credentials
ADMIN_USER = "admin"
ADMIN_PASS = "password"

# ----------------- ROUTES -------------------

@app.route('/')
def index():
    conn = get_db_connection()

    # Filters
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

    query += ' ORDER BY price ' + ('DESC' if sort_order == 'desc' else 'ASC')

    products = conn.execute(query, params).fetchall()

    materials = [row[0] for row in conn.execute('SELECT DISTINCT material FROM products WHERE material IS NOT NULL')]
    product_types = [row[0] for row in conn.execute('SELECT DISTINCT product_type FROM products WHERE product_type IS NOT NULL')]

    conn.close()

    return render_template('index.html', products=products, materials=materials, product_types=product_types)


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

    conn = get_db_connection()
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

        # Main image
        main_image_file = request.files.get('image')
        main_image_filename = secure_filename(main_image_file.filename)
        main_image_path = os.path.join(app.config['UPLOAD_FOLDER'], main_image_filename)
        main_image_file.save(main_image_path)

        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute('''
            INSERT INTO products (title, description, price, image, material, product_type)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (title, desc, price, main_image_filename, material, product_type))
        product_id = cur.lastrowid

        # Additional images
        extra_files = request.files.getlist('extra_images')
        for file in extra_files:
            if file and file.filename:
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                cur.execute('INSERT INTO product_images (product_id, filename) VALUES (?, ?)', (product_id, filename))

        conn.commit()
        conn.close()
        return redirect(url_for('dashboard'))

    return render_template('add_product.html')


@app.route('/edit/<int:product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    if not session.get('admin'):
        return redirect(url_for('login'))

    conn = get_db_connection()

    if request.method == 'POST':
        title = request.form['title']
        desc = request.form['description']
        price = request.form['price']
        material = request.form['material']
        product_type = request.form['product_type']

        # Handle main image update
        old_image = conn.execute('SELECT image FROM products WHERE id = ?', (product_id,)).fetchone()['image']
        file = request.files.get('image')
        image = old_image
        if file and file.filename:
            image = secure_filename(file.filename)
            path = os.path.join(app.config['UPLOAD_FOLDER'], image)
            file.save(path)

        # Update main product info
        conn.execute('''
            UPDATE products SET title=?, description=?, price=?, image=?, material=?, product_type=? WHERE id=?
        ''', (title, desc, price, image, material, product_type, product_id))

        # Handle deleting extra images
        to_delete = request.form.getlist('delete_images')
        for filename in to_delete:
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            if os.path.exists(file_path):
                os.remove(file_path)
            conn.execute('DELETE FROM product_images WHERE filename = ? AND product_id = ?', (filename, product_id))

        # Handle new extra image uploads
        extra_files = request.files.getlist('images')
        for file in extra_files:
            if file and file.filename:
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                conn.execute('INSERT INTO product_images (product_id, filename) VALUES (?, ?)', (product_id, filename))

        conn.commit()
        conn.close()
        return redirect(url_for('dashboard'))

    # GET request: fetch product and associated images
    product = conn.execute('SELECT * FROM products WHERE id = ?', (product_id,)).fetchone()
    images = [row['filename'] for row in conn.execute(
        'SELECT filename FROM product_images WHERE product_id = ?', (product_id,)
    )]
    conn.close()

    return render_template('edit_product.html', product=product, images=images)
@app.route('/delete/<int:product_id>')
def delete_product(product_id):
    if not session.get('admin'):
        return redirect(url_for('login'))

    conn = get_db_connection()
    conn.execute('DELETE FROM product_images WHERE product_id = ?', (product_id,))
    conn.execute('DELETE FROM products WHERE id = ?', (product_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('dashboard'))


@app.route('/product/<int:id>')
def product_detail(id):
    conn = get_db_connection()
    product = conn.execute('SELECT * FROM products WHERE id = ?', (id,)).fetchone()
    if not product:
        return "Termék nem található", 404

    images = [product['image']]  # Main image first
    extra_images = conn.execute('SELECT filename FROM product_images WHERE product_id = ?', (id,)).fetchall()
    images += [row['filename'] for row in extra_images]
    conn.close()
    return render_template('product_detail.html', product=product, images=images)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5003))
    app.run(host='0.0.0.0', port=port)
