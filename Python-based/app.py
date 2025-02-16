from flask import Flask, render_template, request, redirect, session, url_for
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Database configuration
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': 'Kavi1021',
    'database': 'ecommerce'
}

# Routes
@app.route('/')
def home():
    if 'user_id' in session:
        # Redirect logged-in users to the index page
        return redirect(url_for('index'))
    # For non-logged-in users, show the login page
    return render_template('login.html')

@app.route('/search')
def search():
    query = request.args.get('query', '').strip()
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)
    sql = "SELECT * FROM items WHERE name LIKE %s OR description LIKE %s"
    cursor.execute(sql, (f"%{query}%", f"%{query}%"))
    items = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('index.html', items=items)

@app.route('/index')
def index():
    with mysql.connector.connect(**db_config) as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM items ")
        items = cursor.fetchall()
        cursor.execute("SELECT * FROM items  WHERE category = 'phone' LIMIT 4")
        bags = cursor.fetchall()
    return render_template('index.html', items=items, bags= bags  )
    

@app.route('/category/<string:category_name>')
def category(category_name):
    with mysql.connector.connect(**db_config) as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM items WHERE category = %s", (category_name,))
        items = cursor.fetchall()
    return render_template('index.html', items=items)


@app.route('/order/<int:item_id>')
def order(item_id):
    # Connect to MySQL to fetch the specific item's details
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM items WHERE id = %s", (item_id,))
    item = cursor.fetchone()
    conn.close()

    if item:
        return render_template('order.html', item=item)
    else:
        return "<h1>Item not found</h1>", 404
@app.route('/place_order', methods=['POST'])
def place_order():
    # Debugging: Print the form data to verify it
    print("Form Data Received:")
    print(request.form)

    # Get the order details from the form
    item_id = request.form['item_id']
    item_name = request.form['item_name']
    item_price = request.form['item_price']
    user_name = request.form['user_name']
    user_address = request.form['user_address']
    user_phone = request.form['user_phone']
    # Connect to the database
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()

    # Insert the order into the orders table
    cursor.execute("""
        INSERT INTO orders (item_id, item_name, item_price, user_name, user_address, user_phone) 
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (item_id, item_name, item_price, user_name, user_address, user_phone))

    # Commit and close the connection
    conn.commit()
    cursor.close()
    conn.close()

    return "<h1>Order placed successfully!</h1><a href='/'>Go Back to Home</a>"

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])

        with mysql.connector.connect(**db_config) as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, password))
            conn.commit()
        return redirect(url_for('login'))

    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        with mysql.connector.connect(**db_config) as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
            user = cursor.fetchone()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            return redirect(url_for('index'))
        else:
            return "<h1>Invalid username or password</h1>"

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

@app.route('/add_to_cart/<int:item_id>')
def add_to_cart(item_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']

    with mysql.connector.connect(**db_config) as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM items WHERE id = %s", (item_id,))
        item = cursor.fetchone()

        if item:
            cursor.execute("""
                INSERT INTO cart (user_id, item_id, item_name, item_price, quantity)
                VALUES (%s, %s, %s, %s, 1)
            """, (user_id, item['id'], item['name'], item['price']))
            conn.commit()

    return redirect(url_for('view_cart'))

@app.route('/view_cart')
def view_cart():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']

    with mysql.connector.connect(**db_config) as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM cart WHERE user_id = %s", (user_id,))
        cart_items = cursor.fetchall()

    return render_template('cart.html', cart_items=cart_items)

@app.route('/increase_quantity', methods=['POST'])
def increase_quantity():
    cart_id = request.form.get('item_id')
    if not cart_id:
        return "Error: item_id is missing", 400

    with mysql.connector.connect(**db_config) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE cart SET quantity = quantity + 1 WHERE id = %s", (cart_id,))
        conn.commit()

    return redirect(url_for('view_cart'))


@app.route('/decrease_quantity', methods=['POST'])
def decrease_quantity():
    cart_id = request.form.get('item_id')
    if not cart_id:
        return "Error: item_id is missing", 400

    with mysql.connector.connect(**db_config) as conn:
        cursor = conn.cursor()
        # Ensure quantity does not go below 1
        cursor.execute("UPDATE cart SET quantity = GREATEST(quantity - 1, 1) WHERE id = %s", (cart_id,))
        conn.commit()

    return redirect(url_for('view_cart'))

@app.route('/delete_from_cart', methods=['POST'])
def delete_from_cart():
    cart_id = request.form.get('cart_id')

    if not cart_id:
        return "Error: cart_id is missing", 400

    with mysql.connector.connect(**db_config) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM cart WHERE id = %s", (cart_id,))
        conn.commit()

    return redirect(url_for('view_cart'))

@app.route('/checkout', methods=['POST'])
def checkout():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    user_name = request.form['user_name']
    user_address = request.form['user_address']
    user_phone = request.form['user_phone']

    with mysql.connector.connect(**db_config) as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM cart WHERE user_id = %s", (user_id,))
        cart_items = cursor.fetchall()

        for item in cart_items:
            cursor.execute("""
                INSERT INTO orders (item_id, item_name, item_price, quantity, user_name, user_address, user_phone)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (item['item_id'], item['item_name'], item['item_price'], item['quantity'], user_name, user_address, user_phone))

        cursor.execute("DELETE FROM cart WHERE user_id = %s", (user_id,))
        conn.commit()

    return "<h1>Order placed successfully!</h1><a href='/'>Go Back to Home</a>"
@app.route('/category/bag')
def category_bag():
    with mysql.connector.connect(**db_config) as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM items WHERE category = %s", ('bag',))
        items = cursor.fetchall()
    return render_template('category_bag.html', items=items)
# Main
if __name__ == '__main__':
    app.run(debug=True)
