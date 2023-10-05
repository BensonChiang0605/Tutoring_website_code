from flask import render_template, request, Blueprint
from main.models import Post

main_main = Blueprint('main_main', __name__)

@main_main.route("/")
@main_main.route("/home")  # route
def home():  # function name
    page = request.args.get('page', 1, type=int)
    posts = Post.query.order_by(Post.date_posted.desc()).paginate(page=page, per_page=4)
    return render_template('home.html', posts=posts)


@main_main.route("/about")
def about():
    return render_template('about.html', title='About')

# @main_main.route("/econ_questionbank", methods=['GET'])
# def econ_questionbank():
#     return render_template('ib_economics_questionbank/index.html', title='Econ Questionbank')