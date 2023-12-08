from flask import render_template, request, redirect, url_for, flash, abort, Blueprint
from flask_login import current_user, login_required
from main import db
from main.models import Post
from main.posts.forms import PostForm, ScanImageForm, is_empty_field
from main.posts.utils import scan_image, correct_spelling, tag_english_essay, filler_feedback
from main.users.utils import save_picture
import json

posts = Blueprint('posts', __name__)

@posts.route("/post/new", methods=['GET', 'POST'])
def new_post():
    form = PostForm()
    if form.validate_on_submit():
        post = Post(title=form.title.data, content=form.content.data, author=current_user)
        db.session.add(post)
        db.session.commit()
        flash('Post created!', 'success')
        return redirect(url_for('main_main.home'))
    return render_template('create_post.html', title='New Post', form=form)

@posts.route("/post/<int:post_id>")
def post(post_id):
    post = Post.query.get_or_404(post_id)

    return render_template('post.html', title=post.title,post=post)

@posts.route("/post/<int:post_id>/update", methods=['GET', 'POST'])
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
        return redirect(url_for('posts.post', post_id=post.id))
    elif request.method == 'GET':
        form.title.data = post.title
        form.content.data = post.content

    return render_template('create_post.html', title=post.title, post=post, form=form)

@posts.route("/post/<int:post_id>/delete", methods=['GET', 'POST'])
@login_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author != current_user: # checks if the logged in user is the author of this post
        abort(403)
    db.session.delete(post)
    db.session.commit()
    flash('Your post has been deleted!', 'success')
    return redirect(url_for('main_main.home'))

@posts.route("/submit_essay", methods=['GET', 'POST'])
@login_required
def submit_essay():

    # could be improved by not skip the step where we save the image, we just read it.
    form = ScanImageForm()
    if form.validate_on_submit():
        scanned_texts = []  # Store scanned texts for all uploaded files
        # question_type = form.question_type.data         #CONTINUE WORKING HERE
        if is_empty_field(form.picture.data):
            spell_checked_essay = form.essay_response.data

        else:
            print(form.picture.data)
            for file in form.picture.data:
                if file:
                    file_content = file.read()

                    scanned_text = scan_image(file_content)
                    scanned_texts.append(scanned_text)
            spell_checked_essay = correct_spelling(''.join(scanned_texts), form.prompt)
            # we cannot fix up spelling for them all the time

        annotated_essay = tag_english_essay(spell_checked_essay, form.prompt)
        filler_feedback = filler_feedback(annotated_essay)
        post = Post(title=form.prompt.data, content=spell_checked_essay, author=current_user, grammar_feedback=annotated_essay + filler_feedback,\
                    econ_feedback=None) # plus other section feedbacks, add later
        db.session.add(post)
        db.session.commit()
        flash('Post created!', 'success')

        return redirect(url_for('main_main.home'))
    return render_template('submit_essay.html', title='Submit Essay', form=form)

@posts.route("/prototype_homepage")
def prototype_homepage():
    image_file = url_for('static', filename='tutoring_logo.svg')
    return render_template('prototype_homepage.html', title='prototype_homepage', image_file=image_file)

@posts.route("/grammar_feedback/<int:post_id>", methods=['GET', 'POST'])
def grammar_feedback(post_id):
    post = Post.query.get_or_404(post_id)
    return render_template('grammar_feedback.html', title='Grammar Feedback', post=post, feedback=post.grammar_feedback) # feedback is annotated essay + filler feedback + awkward words feedback

@posts.route("/econ_feedback/<int:post_id>", methods=['GET', 'POST'])
def econ_feedback_page(post_id):
    post = Post.query.get_or_404(post_id)
    return render_template('econ_feedback.html', title='Econ Feedback', post=post, econ_feedback=post.econ_feedback)

# Creating a route to handle a webpage where users/moderators can change the content of GPT feedback
# @app.route("/econ_feedback/<int:post_id>/edit", methods=['GET', 'POST'])
# def handle_html_submission(post_id):
#     post = Post.query.get_or_404(post_id)
#     econ_feedback = post.econ_feedback
#
#     # Sanitize and process the HTML content
#     # ...
#     return 'HTML content received and processed!'