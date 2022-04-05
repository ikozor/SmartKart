from flask import Blueprint, render_template, session, redirect, url_for, request, flash
views = Blueprint('views', __name__)
from . import mysql

# all routes in views.py are things the user can look at after they signed in to our app

# renders the html files when the these urls are used, and also gets data from the
# html file to either log user in or create a new user

# Checks if the user is logged in if they are they are redirected to the homepage
@views.route('/')
def home():
    if not session.get("name"):
        return redirect(url_for('auth.login'))
    return render_template("home.html", active = (session.get('name')!=None))

# Takes the user input and checks for the item after the search button is clicked
@views.route('/search', methods=['POST'])
def search():
    if not session.get("name"):
        return redirect(url_for('auth.login'))
    search = request.form.get('search')
    cur = mysql.connection.cursor()
    # Grabs the Product_Name to be displayed on the UI when user searches for a product.
    cur.execute("SELECT Product_ID,Product_Name,Weight,Weight_type FROM PRODUCTS WHERE Product_Name LIKE '%"+search+"%' AND Quantity > 0 GROUP BY Product_Name")
    produce = cur.fetchall()

    # Grabs the Store_Name and Store_Zip to be displayed on the UI when the user is prompted to select the item from a specific store.
    cur.execute("SELECT Product_ID, Product_Name,Store_Name, Store_Zip,Product_Price FROM STORES, PRODUCTS WHERE STORES.Store_ID = PRODUCTS.Store_ID AND Product_Name LIKE '%"+search+"%' AND Quantity > 0 ")
    prod_price = cur.fetchall()
    cur.close()
    return render_template('search.html',search = search, produce = produce, prod_price = prod_price, active = (session.get('name')!=None))

# When the add to cart button is pressed checks if the item is in stock and adds it to the INCART table
@views.route('/add_to_cart',methods=['POST'])
def add_to_cart():
    product =  request.form['stores']
    quantity = request.form.get('quantity')

    cur = mysql.connection.cursor()

    if quantity and int(quantity)>0:
        # See if row exists in the INCART table
        cur.execute("SELECT Quantity FROM INCART WHERE Product_ID = %(product)s AND Customer_ID = %(customer)s", {'product':product , 'customer': session.get('name')})
        amt = cur.fetchone()
        if amt:
            cur.execute("UPDATE INCART SET Quantity = %(quantity)s WHERE Product_ID = %(product)s AND Customer_ID = %(customer)s", {'quantity':(int(quantity) + amt[0]), 'product':product, 'customer':session.get('name')})
        else:
            cur.execute("INSERT INTO INCART (Product_ID, Customer_ID, Quantity) VALUES (%s,%s,%s)", (product,session.get("name"),int(quantity)))
        mysql.connection.commit()
        flash('Added to Cart', category='success')
    cur.close()
    return redirect(url_for('views.search'), code =307)

# When the cart button is pressed gets the items from INCART and displays for the user
@views.route('/checkout', methods=['GET','POST'])
def checkout():
    if not session.get('name'):
        return redirect(url_for('auth.login'))
    cur = mysql.connection.cursor()
    if request.method == 'POST':
        quantity = request.form.get('quantity')
        product_id = request.form.get('product_id')
        if quantity and int(quantity)>0:
            cur.execute("UPDATE INCART SET Quantity = %(quantity)s WHERE Product_ID = %(product)s AND Customer_ID = %(customer)s", {'quantity':quantity , 'product':product_id, 'customer':session.get('name')})
        elif quantity:
            cur.execute("DELETE FROM INCART WHERE Product_ID = %(product)s AND Customer_ID = %(customer)s", {'quantity':quantity , 'product':product_id, 'customer':session.get('name')})
        mysql.connection.commit()




    cur.execute("SELECT PRODUCTS.Product_ID, PRODUCTS.Quantity, INCART.Quantity FROM PRODUCTS, INCART WHERE PRODUCTS.Product_ID = INCART.Product_ID")
    quancheck = cur.fetchall()
    for prod in quancheck:
        if prod[2] > prod[1]:
            cur.execute("UPDATE INCART SET Quantity = %(quant)s WHERE Product_ID = %(product)s", {'quant':prod[1], 'product':prod[0]})
            mysql.connection.commit()

    cur.execute("""Select INCART.Product_ID, STORES.Store_Name, PRODUCTS.Product_Name, PRODUCTS.Product_Price, PRODUCTS.Weight, PRODUCTS.Weight_type, INCART.Quantity, PRODUCTS.Quantity
    FROM INCART, PRODUCTS, STORES
    WHERE PRODUCTS.Product_ID = INCART.Product_ID AND STORES.Store_ID = PRODUCTS.Store_ID AND INCART.Customer_ID = %(user)s """, {'user':session.get('name')})
    products = cur.fetchall()

    cur.execute("SELECT Customer_Zip FROM CUSTOMERS WHERE Customer_ID = %(customer)s", {'customer': session.get('name')})
    zipcode = cur.fetchone()
    cur.close()
    sum = 0
    for product in products:
        sum += product[3]*product[6]

    return render_template('checkout.html',products = products, length = len(products), sum = sum, zipcode = zipcode[0] ,active = (session.get('name')!=None))

# When order items is pressed from the checkout. It displays information from the order.
@views.route('/order_placed', methods=['POST'])
def place_order():
    if not session.get('name'):
        return redirect(url_for('auth.login'))
    cur = mysql.connection.cursor()

    cur.execute("SELECT Product_ID, Quantity FROM INCART WHERE Customer_ID = %(customer)s",{'customer':session.get('name')})
    products = cur.fetchall()
    cur.execute("INSERT INTO ORDERS (Order_ID, Customer_ID, Order_Date, Quantity) VALUES (NULL,%s,(SELECT CURDATE()),%s)",  (session.get('name'), len(products)))
    mysql.connection.commit()
    cur.execute("SELECT LAST_INSERT_ID()")
    id = cur.fetchone()
    for product in products:
        cur.execute("INSERT INTO ORDER_ITEMS(Order_ID, Product_ID, Quantity) VALUES (%s,%s,%s)", (id[0], product[0], product[1]))
        cur.execute("UPDATE PRODUCTS SET Quantity = Quantity-%(sold)s WHERE Product_ID=%(prod)s",{'sold':product[1], 'prod':product[0]})
    cur.execute("DELETE FROM INCART WHERE Customer_ID = %(customer)s", {'customer': session.get('name')})
    mysql.connection.commit()
    cur.close()
    flash('Order ' + str(id[0]) + ' placed', category='success')
    return redirect(url_for('views.orders'))

# When orders is looked at gives all the items in the order for the user
@views.route('orders')
def orders():
    if not session.get('name'):
        return redirect(url_for('auth.login'))
    cur = mysql.connection.cursor()

    cur.execute("""SELECT ORDERS.Order_ID, ORDERS.Order_Date, ORDERS.Quantity AS Item_types, PRODUCTS.Product_Name, ORDER_ITEMS.Quantity AS amount
    FROM ORDERS, ORDER_ITEMS, PRODUCTS
    WHERE ORDERS.Order_ID = ORDER_ITEMS.Order_ID AND PRODUCTS.Product_ID = ORDER_ITEMS.Product_ID AND ORDERS.Customer_ID = %(customer)s
    ORDER BY ORDERS.Order_ID DESC""", {'customer':session.get('name')})

    items = cur.fetchall()
    orders = []
    item = 0
    while item < len(items):
        order = [items[item][0], items[item][1]]
        order_items = []
        for i in range(items[item][2]):
            the_item = [items[item][3], items[item][4]]
            order_items.append(the_item)
            item+=1;
        order.append(order_items)
        orders.append(order)

    return render_template("orders.html", orders = orders, active = (session.get('name')!=None))

# Selects all products from the order and takes user to the checkout page with the information gathered
@views.route('copy_order', methods= ['POST'])
def copy_order():
    order_id = request.form.get('order')
    cur = mysql.connection.cursor()
    cur.execute("SELECT Product_ID, Quantity FROM ORDER_ITEMS WHERE Order_ID = %(order)s", {'order':order_id})
    items = cur.fetchall()
    for item in items:
        cur.execute("SELECT Quantity FROM PRODUCTS WHERE Product_ID = %(product)s", {'product':item[0]})
        curprod = cur.fetchone()
        if curprod[0] > 0:
            cur.execute("INSERT INTO INCART(Customer_ID, Product_ID, Quantity) VALUES (%s,%s,%s)", (session.get('name'),item[0],item[1]))
    mysql.connection.commit()
    return redirect(url_for('views.checkout'))





















