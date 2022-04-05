from flask import Blueprint, render_template, request, flash, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from . import mysql
import re


auth = Blueprint('auth', __name__)

# all routes in auth.py are for making sure that the user is logged in to use our application

# renders the html files when the these urls are used, and also gets data from the
# html file to either log user in or create a new user

# Responsible for the user login to the application
@auth.route('/login', methods=['GET', 'POST',])
def login():

    # start a connection to mysql server and do mysql commands here

    cur = mysql.connection.cursor()
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        cur.execute("SELECT Customer_ID, Customer_Email,Customer_Login_Password FROM CUSTOMERS WHERE Customer_Email = %(email)s", {'email':email})
        account = cur.fetchone()
        if account:
            if check_password_hash(account[2], password):
                cur.close()
                flash('Logged In', category='success')
                session['name'] = account[0]
                return redirect(url_for('views.home'))
            else:
                flash('Incorrect Password', category='error')
        else:
            flash('Account with that email was not found', category='error')

    cur.close()
    return render_template("login.html")

# Responsible for the user logout of the application
@auth.route('/logout')
def logout():
    session['name'] = None
    return redirect(url_for('auth.login'))

# Responsible for the user signup process of our application
@auth.route('signup', methods=['GET', 'POST',])
def signup():
    if request.method == 'POST':
        email = request.form.get('email')
        full_name = request.form.get('full_name')
        phone_number = request.form.get('phone_number')
        zipcode = request.form.get('zipcode')
        password = request.form.get('password')
        password2 = request.form.get('password2')

        # start a connection to mysql server and do mysql commands here
        cur = mysql.connection.cursor()
        cur.execute("SELECT Customer_Email FROM CUSTOMERS WHERE Customer_Email = %(email)s", {'email':email})
        email_exists = cur.fetchall()
        regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'


        if email_exists:
            flash('Email already in use', category='error')
        elif not re.fullmatch(regex, email):
            flash('Invalid Email', category='error')
        elif len(full_name) < 3:
            flash('Invalid Full Name',category='error')
        elif not zipcode.isnumeric():
            flash('Zipcode is not valid',category='error')
        elif password != password2:
            flash('Passwords do not match',category='error')
        elif len(password) < 8:
            flash('Password must be at least 8 characters',category='error')
        else:
            pw = generate_password_hash(password, method = 'sha256')

            cur.execute("INSERT INTO CUSTOMERS(Customer_ID, Customer_Name, Customer_Zip, Customer_Email, Customer_Phone, Customer_Login_Password) VALUES(%s,%s,%s,%s,%s,%s)",("NULL",full_name, zipcode,email,phone_number, pw))
            mysql.connection.commit()
            flash('Account Created', category='success')

            cur.execute("SELECT Customer_ID FROM CUSTOMERS WHERE Customer_Email = %(email)s", {'email':email})
            account = cur.fetchone()
            cur.close()
            session['name'] = account[0]
            # No sql commands past this

            return redirect(url_for('views.home'))



    return render_template("sign_up.html")

# Responsible for checking for an item
def check_list_for(a_list, value):
    for i in a_list:
        for j in i:
            if value == j:
                return True
    return False