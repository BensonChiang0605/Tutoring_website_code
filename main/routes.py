from PIL import Image
import os
import secrets
from flask import render_template, url_for, flash, redirect, request, abort
from main import app, db, bcrypt
from main.forms import RegistrationForm, LoginForm, UpdateAccountForm, PostForm, ScanImageForm
from main.models import User, Post
from flask_login import login_user, current_user, logout_user, login_required
import openai
import re

# Cameralyze
import requests
import json
import base64
import cameralyze


@app.route("/")
@app.route("/home")  # route
def home():  # function name
    page = request.args.get('page', 1, type=int)
    posts = Post.query.order_by(Post.date_posted.desc()).paginate(page=page, per_page=2)
    return render_template('home.html', posts=posts)


@app.route("/about")
def about():
    return render_template('about.html', title='About')


@app.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(('home'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username=form.username.data, email=form.email.data, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash(f'Your account has been created! You are able to log in!', 'success')
        return redirect(url_for('home'))
    return render_template('register.html', title='Register', form=form)


@app.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(('home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('home'))
        else:
            flash('Login Unsuccessful. Please check username and password', 'danger')
    return render_template('login.html', title='Login', form=form)


@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('home'))


def save_picture(form_picture):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(app.root_path, 'static/profile_pics', picture_fn)

    #output_size = (125, 125)
    i = Image.open(form_picture)
    #i.thumbnail(output_size)

    i.save(picture_path)

    return picture_fn


@app.route("/account", methods=['GET', 'POST'])
@login_required
def account():
    form = UpdateAccountForm()
    if form.validate_on_submit():
        if form.picture.data:
            picture_file = save_picture(form.picture.data)
            current_user.image_file = picture_file
        current_user.username = form.username.data
        current_user.email = form.email.data
        db.session.commit()
        flash('Your account has been updated!', 'success')
        return redirect(url_for('account'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
    image_file = url_for('static', filename='profile_pics/' + current_user.image_file)
    return render_template('account.html', title='Account', image_file=image_file, form=form)


@app.route("/post/new", methods=['GET', 'POST'])
def new_post():
    form = PostForm()
    if form.validate_on_submit():
        post = Post(title=form.title.data, content=form.content.data, author=current_user)
        db.session.add(post)
        db.session.commit()
        flash('Post created!', 'success')
        return redirect(url_for('home'))
    return render_template('create_post.html', title='New Post', form=form)

@app.route("/post/<int:post_id>")
def post(post_id):
    post = Post.query.get_or_404(post_id)

    return render_template('post.html', title=post.title,post=post)

@app.route("/post/<int:post_id>/update", methods=['GET', 'POST'])
@login_required
def update_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author != current_user: # checks if the logged in user is the author of this post
        abort(403)

    form = PostForm()
    if form.validate_on_submit():
        post.title = form.title.data
        post.content = form.content.data
        db.session.commit()
        flash('Your post has been updated!', 'success')
        return redirect(url_for('post', post_id=post.id))
    elif request.method == 'GET':
        form.title.data = post.title
        form.content.data = post.content

    return render_template('create_post.html', title=post.title, post=post, form=form)

@app.route("/post/<int:post_id>/delete", methods=['GET', 'POST'])
@login_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author != current_user: # checks if the logged in user is the author of this post
        abort(403)
    db.session.delete(post)
    db.session.commit()
    flash('Your post has been deleted!', 'success')
    return redirect(url_for('home'))

@app.route("/user/<string:username>")
def user_posts(username):
    page = request.args.get('page', 1, type=int)
    user = User.query.filter_by(username=username).first_or_404()
    posts = Post.query.filter_by(author=user).order_by(Post.date_posted.desc()).paginate(page=page, per_page=5)
    return render_template('user_posts.html', posts=posts, user=user)

def scan_image(picture_file):
    headers = {
        "x-api-key": "7fUS8uJUSI1ZOIT9"
    }

    payload = {
        "itemUuid": "4eef90ef-00df-42a2-b152-69109a9a8602",
        "image": jpg_to_base64(picture_file),
        "rawResponse": True,
        "configuration": {}
    }

    response = requests.post("https://inference.plugger.ai/", headers=headers, json=payload)

    result = response.json()
    text_in_image = result["data"][0]["text"]
    return text_in_image

def correct_grammar(scanned_texts, essay_question):
    openai.api_key = "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"

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {
                "role": "system",
                "content": f"You'll receive a text generated by an image-to-text app in response to the question '{essay_question}'. Your task is to correct any grammatical and logical errors while preserving the original meaning."
            },
            {
                "role": "user",
                "content": f"{scanned_texts}"
            },
        ],
        temperature=1,
        max_tokens=3500,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0
    )

    assistant_reply = response['choices'][0]['message']['content']
    return assistant_reply

def correct_spelling(scanned_texts, essay_question):
    openai.api_key = "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"

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {
                "role": "user",
                "content": f"I got this scanned text from an image to text application, please fix basic spelling errors\
                 and remove unnecessary line breaks but do not fix grammatical mistakes such as \n- Subject-Verb Agreement Errors \
                 \n- Misplaced or Dangling Modifiers \n- Wrong tense or verb form \n- Incorrect use of articles and prepositions\
                \nText: {scanned_texts}"
            },
        ],
        temperature=1,
        max_tokens=3500,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0
    )

    assistant_reply = response['choices'][0]['message']['content']
    return assistant_reply
def gpt_grammar_feedback(spell_checked_essay):
    openai.api_key = "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"

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {
                "role": "user",
                "content": "Identify grammar mistakes and poorly constructed sentences in this text.  First extract all sections where there is an issue, then summarise each issue you see, then make edits to improve the identified mistake, and finally explain your edits. Output your response in JSON.\n\nText: The circular flow diagram is a diagram that shows the relationship between households, firms, government, financial markets, and other countries in a market, how money flows in the system, and how government, financial markets, and other countries are involved in this closed system. The simple circular flow diagram only focused on the money flows between households and firms, which is a closed system. \nHowever, money will not always be in the system for households and firms. A portion of the money within the system will flow out to the government, financial markets, and other countries, which forms the complex circular flow diagram and shows how these injections and leakages work in the closed system. The government creates leakages through taxes, and injections through government spending. \nIn this case, households receive factor payments and dividends, including wages, profit, interest, and rent; meanwhile, they provide factors of production, which are land, labor, capital, and entrepreneurship, to firms. Furthermore, firms provide goods and services to households; at the same time, the expenditure on the goods and services will return to firms.\nFor the government, the leakage will be the taxes that are paid by households and firms four times a year, and this money will flow out of the system. For example, there are income taxes, sales taxes, etc. As a Taiwanese, Taiwan’s income taxes increase from 5% to 12% to 20% to 30% to 40% while the income increases; moreover, the sale tax in Taiwan is 5%. \nBesides, the money that is added to the system, which is also known as the injection, will be government spending and transfers. Due to the circular flow diagram, these taxes will be used for government spending and transfers. For instance, the government will use this money to build or renew infrastructure, pay for health care and education for citizens, provide military funds, etc. According to data, the Taiwan government used 6.6% of the GDP for health care. These examples illustrate how the government provides injections and leakages to involve the circular flow diagram."
            },
            {
                "role": "assistant",
                "content": """{\n    \"problem_summaries\": [\n        \"Lack of parallelism in the list of items.\",\n        \"Lack of clarity and wordiness.\"\n    ],\n    \"original_sentences\": [\n        \"The circular flow diagram shows the relationship between households, firms, government, financial markets, and other countries in a market, how money flows in the system, and how government, financial markets, and other countries are involved in this closed system.\",\n        \"The simple circular flow diagram only focused on the money flows between households and firms, which is a closed system.\"\n    ],\n    \"revised_sentences\": [\n        \"The circular flow diagram illustrates the relationships among households, firms, government, financial markets, and other countries in a market, the flow of money in the system, and the involvement of government, financial markets, and other countries in this closed system.\",\n        \"The basic circular flow diagram solely focuses on the money exchange between households and firms, creating a closed system\"\n    ],\n    \"explanations\": [\n        \"I revised the sentence to maintain parallelism by listing all items in the same grammatical form.\",\n        \"I rephrased the sentence to make it clearer and more concise.\"\n}"""

            },
            {
                "role": "user",
                "content": f"Text:{spell_checked_essay}"
            }
        ],
        temperature=0.59,
        max_tokens=1297,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0
    )
    assistant_reply = response['choices'][0]['message']['content']
    return assistant_reply

def jpg_to_base64(image_path):
    with open(image_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read())

    # Convert the bytes-like object to a string
    image_string = encoded_string.decode("utf-8")
    return image_string
@app.route("/submit_essay", methods=['GET', 'POST'])
@login_required
def submit_essay():
    # form = ScanImageForm()
    # if form.validate_on_submit():
    #     if form.picture.data:
    #         picture_file = save_picture(form.picture.data)
    #         scanned_text = scan_image(f"main/static/profile_pics/{picture_file}")   # could be improved by not skip the step where we save the image, we just read it.
    form = ScanImageForm()
    if form.validate_on_submit():
        scanned_texts = []  # Store scanned texts for all uploaded files
        for file in form.picture.data:
            if file:
                picture_file = save_picture(file)
                scanned_text = scan_image(f"main/static/profile_pics/{picture_file}")
                scanned_texts.append(scanned_text)
        spell_checked_essay = correct_spelling(''.join(scanned_texts), form.prompt)
        # load grammar feedback to of this post into the this post model
        post = Post(title=f"{current_user.username} response to '{form.prompt.data}'",\
                    content=spell_checked_essay, author=current_user, grammar_feedback=gpt_grammar_feedback(spell_checked_essay))
        db.session.add(post)
        db.session.commit()
        flash('Post created!', 'success')

        return redirect(url_for('home'))
    return render_template('submit_essay.html', title='Submit Essay', form=form)

@app.route("/prototype_homepage")
def prototype_homepage():
    image_file = url_for('static', filename='tutoring_logo.svg')
    return render_template('prototype_homepage.html', title='prototype_homepage', image_file=image_file)

def add_span_tags(text, sentences_to_tag):
    # Split the text into sentences using regular expressions
    sentences = re.split(r'(?<=[.!?])\s+', text)

    # Initialize a variable to store the result
    result = ""

    # Initialize a unique ID counter
    unique_id = 1

    for sentence in sentences:
        # Check if the current sentence is in the list
        if sentence in sentences_to_tag:
            # Add a <span> tag with a unique ID
            result += f'<span id="problem-{unique_id}">{sentence}</span> '
            unique_id += 1
        else:
            result += sentence + ' '

    return result.strip()

def add_span_tags_to_text(text, sentences_to_tag):
    # Split the text into sentences using regular expressions
    sentences = re.split(r'(?<=[.!?])\s+', text)

    # Initialize a variable to store the result
    result = ""

    # Initialize a unique ID counter
    unique_id = 1

    for sentence in sentences:
        # Check if the current sentence is in the list
        if sentence in sentences_to_tag:
            # Add a <span> tag with a unique ID
            result += f'<span id="problem-{unique_id}">{sentence}</span> '
            unique_id += 1
        else:
            result += sentence + ' '

    return result.strip()
@app.route("/grammar_feedback/<int:post_id>", methods=['GET', 'POST'])
def grammar_correction_prototype(post_id):
    post = Post.query.get_or_404(post_id)
    json_data = json.loads(post.grammar_feedback)
    highlightable_essay = add_span_tags_to_text(post.content, list(json_data["original_sentences"]))
    return render_template('grammar_feedback.html', title='Grammar Feedback', post=post, highlightable_essay=highlightable_essay, revised_sentences=json_data["revised_sentences"],\
                           problem_summaries=json_data["problem_summaries"], explanations=json_data["explanations"],original_sentences=json_data["original_sentences"])
