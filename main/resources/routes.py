from flask import render_template, request, redirect, url_for, flash, abort, Blueprint
from flask_login import current_user, login_required
from main import db

resources = Blueprint('resources', __name__)

@resources.route("/resource_page")
def resource_page():
    return render_template('resource_page.html', title='Resource Page')