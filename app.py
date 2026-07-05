from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3

app = Flask(__name__)
app.secret_key = "cravekitchen_secret_2026"
DB_NAME = "food.db"
ADMIN_PASSWORD = "mypassword123"


def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS foods (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            category TEXT,
            description TEXT,
            image TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT NOT NULL,
            food_name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            total_price REAL NOT NULL
        )
    ''')
    conn.commit()
    conn.close()


def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


@app.route('/')
def home():
    conn = get_db_connection()
    popular_foods = conn.execute('SELECT * FROM foods ORDER BY id DESC LIMIT 11').fetchall()
    conn.close()
    return render_template('home.html', popular_foods=popular_foods)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        password = request.form['password']
        if password == ADMIN_PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('menu'))
        else:
            return render_template('login.html', error="Wrong password")
    return render_template('login.html', error=None)


@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('menu'))


@app.route('/menu')
def menu():
    category_filter = request.args.get('category')
    search_query = request.args.get('search')
    conn = get_db_connection()

    if search_query:
        foods = conn.execute('SELECT * FROM foods WHERE name LIKE ?', ('%' + search_query + '%',)).fetchall()
    elif category_filter:
        foods = conn.execute('SELECT * FROM foods WHERE category = ?', (category_filter,)).fetchall()
    else:
        foods = conn.execute('SELECT * FROM foods').fetchall()

    categories = conn.execute('SELECT DISTINCT category FROM foods').fetchall()
    conn.close()
    return render_template('menu.html', foods=foods, categories=categories)


@app.route('/add-food', methods=['GET', 'POST'])
def add_food():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    if request.method == 'POST':
        name = request.form['name']
        price = request.form['price']
        category = request.form['category']
        description = request.form['description']
        image = request.form['image']

        conn = get_db_connection()
        conn.execute(
            'INSERT INTO foods (name, price, category, description, image) VALUES (?, ?, ?, ?, ?)',
            (name, price, category, description, image)
        )
        conn.commit()
        conn.close()
        return redirect(url_for('menu'))

    return render_template('add_food.html')


@app.route('/delete-food/<int:food_id>')
def delete_food(food_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    conn = get_db_connection()
    conn.execute('DELETE FROM foods WHERE id = ?', (food_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('menu'))


@app.route('/edit-food/<int:food_id>', methods=['GET', 'POST'])
def edit_food(food_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    conn = get_db_connection()
    food = conn.execute('SELECT * FROM foods WHERE id = ?', (food_id,)).fetchone()

    if request.method == 'POST':
        name = request.form['name']
        price = request.form['price']
        category = request.form['category']
        description = request.form['description']
        image = request.form['image']

        conn.execute(
            'UPDATE foods SET name=?, price=?, category=?, description=?, image=? WHERE id=?',
            (name, price, category, description, image, food_id)
        )
        conn.commit()
        conn.close()
        return redirect(url_for('menu'))

    conn.close()
    return render_template('edit_food.html', food=food)


@app.route('/order/<int:food_id>', methods=['GET', 'POST'])
def order(food_id):
    conn = get_db_connection()
    food = conn.execute('SELECT * FROM foods WHERE id = ?', (food_id,)).fetchone()

    if not food:
        conn.close()
        return "Sorry, this food item doesn't exist or has been removed.", 404

    if request.method == 'POST':
        step = request.form.get('step')
        customer_name = request.form['customer_name']
        quantity = int(request.form['quantity'])
        payer_bank = request.form['payer_bank']
        phone = request.form['phone']
        street = request.form['street']
        landmark = request.form['landmark']
        city = request.form['city']
        total_price = food['price'] * quantity

        if step == 'review':
            conn.close()
            return render_template('order_review.html', food=food, customer_name=customer_name,
                                    quantity=quantity, payer_bank=payer_bank, phone=phone,
                                    street=street, landmark=landmark, city=city, total_price=total_price)

        conn.execute(
            'INSERT INTO orders (customer_name, food_name, quantity, total_price, payer_bank, status, phone, street, landmark, city) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (customer_name, food['name'], quantity, total_price, payer_bank, 'Pending', phone, street, landmark, city)
        )
        conn.commit()
        conn.close()
        return render_template('order_success.html', customer_name=customer_name, food=food, quantity=quantity, total_price=total_price)

    conn.close()
    return render_template('order.html', food=food)

@app.route('/orders')
def orders():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    conn = get_db_connection()
    all_orders = conn.execute('SELECT * FROM orders ORDER BY id DESC').fetchall()

    orders_with_images = []
    total_revenue = 0
    for order in all_orders:
        food = conn.execute('SELECT image FROM foods WHERE name = ?', (order['food_name'],)).fetchone()
        order_dict = dict(order)
        order_dict['image'] = food['image'] if food else None
        orders_with_images.append(order_dict)
        if order['status'] == 'Paid':
            total_revenue += order['total_price']

    conn.close()
    return render_template('orders.html', orders=orders_with_images, total_revenue=total_revenue)


@app.route('/mark-paid/<int:order_id>')
def mark_paid(order_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    conn = get_db_connection()
    conn.execute('UPDATE orders SET status = ? WHERE id = ?', ('Paid', order_id))
    conn.commit()
    conn.close()
    return redirect(url_for('orders'))
    
    
@app.route('/delete-order/<int:order_id>')
def delete_order(order_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    conn = get_db_connection()
    conn.execute('DELETE FROM orders WHERE id = ?', (order_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('orders'))


if __name__ == '__main__':
    init_db()
    app.run(debug=False)