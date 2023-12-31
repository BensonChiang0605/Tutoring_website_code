import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager

app = Flask(__name__)
app.config['SECRET_KEY'] = '5791628bb0b13ce0c676dfde280ba245'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'users.login'
login_manager.login_message_category = 'info'

from main.users.routes import users
from main.posts.routes import posts
from main.main_main.routes import main_main
from main.resources.routes import resources

app.register_blueprint(users)
app.register_blueprint(posts)
app.register_blueprint(main_main)
app.register_blueprint(resources)