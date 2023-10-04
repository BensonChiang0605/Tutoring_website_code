from flask import render_template, request, redirect, url_for, flash, abort, Blueprint
from flask_login import current_user, login_required
from main import db
from main.models import Post
from main.posts.forms import PostForm, ScanImageForm
from main.posts.utils import scan_image, gpt_grammar_feedback, correct_spelling, add_span_tags_to_text
import json
import cameralyze

posts = Blueprint('posts', __name__)

@posts.route("/post/new", methods=['GET', 'POST'])
def new_post():
    form = PostForm()
    if form.validate_on_submit():
        post = Post(title=form.title.data, content=form.content.data, author=current_user)
        db.session.add(post)
        db.session.commit()
        flash('Post created!', 'success')
        return redirect(url_for('home'))
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
        return redirect(url_for('post', post_id=post.id))
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
    return redirect(url_for('home'))

@posts.route("/submit_essay", methods=['GET', 'POST'])
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

@posts.route("/prototype_homepage")
def prototype_homepage():
    image_file = url_for('static', filename='tutoring_logo.svg')
    return render_template('prototype_homepage.html', title='prototype_homepage', image_file=image_file)

@posts.route("/grammar_feedback/<int:post_id>", methods=['GET', 'POST'])
def grammar_correction_prototype(post_id):
    post = Post.query.get_or_404(post_id)
    json_data = json.loads(post.grammar_feedback)
    highlightable_essay = add_span_tags_to_text(post.content, list(json_data["original_sentences"]))
    return render_template('grammar_feedback.html', title='Grammar Feedback', post=post, highlightable_essay=highlightable_essay, revised_sentences=json_data["revised_sentences"],\
                           problem_summaries=json_data["problem_summaries"], explanations=json_data["explanations"],original_sentences=json_data["original_sentences"])