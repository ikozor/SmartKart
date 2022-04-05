# having an __init__.py in a folder a python package so we can take the create_app() func and use it in main.py
from flask import Flask
from flask_mysqldb import MySQL

app = Flask(__name__)
mysql = None
#just creates the app
def create_app():
    app.config['MYSQL_HOST'] = ''
    app.config['MYSQL_USER'] = ''
    app.config['MYSQL_PASSWORD'] = ''
    app.config['MYSQL_DB'] = ''

    app.config['SECRET_KEY'] = ""

    from .views import views
    from .auth import auth

    app.register_blueprint(views, url_prefix='/')
    app.register_blueprint(auth, url_prefix='/')

    return app

mysql = MySQL(app)



