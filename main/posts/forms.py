from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField, MultipleFileField
from wtforms.validators import DataRequired, ValidationError
from flask_wtf.file import FileField, FileAllowed, FileRequired

class PostForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    content = TextAreaField('Content', validators=[DataRequired()])
    submit = SubmitField('Post')

class ScanImageForm(FlaskForm):
    prompt = TextAreaField('Enter the essay question', validators=[DataRequired()])
    picture = MultipleFileField('Upload your essay response', validators=[FileAllowed(['jpg','png'])])
    submit = SubmitField('Submit')