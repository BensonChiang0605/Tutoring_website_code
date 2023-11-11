from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField, MultipleFileField, SelectField
from wtforms.validators import DataRequired, ValidationError
from flask_wtf.file import FileField, FileAllowed, FileRequired

def is_empty_field(field_data):
    if field_data:
        if isinstance(field_data, list):
            if not field_data:
                return True
            for file_storage in field_data:
                if not file_storage.filename:  # Check if FileStorage has an empty filename
                    continue
                return False  # Return False if any valid FileStorage object is found
            return True  # If loop completes without returning, all FileStorage objects are empty
        else:
            return not field_data.strip()
    return True


def validate_either_or(form, field):
    print("Essay Data: ", form.essay_response.data)  # Debug
    print("Picture Data: ", form.picture.data)  # Debug

    essay_empty = is_empty_field(form.essay_response.data)
    picture_empty = is_empty_field(form.picture.data)

    # Check if both fields are empty
    if essay_empty and picture_empty:
        raise ValidationError("Please submit either an essay response or a picture.")

    # Check if both fields are filled
    if not essay_empty and not picture_empty:
        raise ValidationError("Please submit either an essay response or a picture, but not both.")


class PostForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    content = TextAreaField('Content', validators=[DataRequired()])
    submit = SubmitField('Post')

# class ScanImageForm(FlaskForm):
#     prompt = TextAreaField('Enter the essay question', validators=[DataRequired()])
#     picture = MultipleFileField('Wrote your essay on paper? Upload the jpg or png images of your written essay:', validators=[FileAllowed(['jpg','png'])])
#     essay_response = TextAreaField('Enter the essay response')
#     submit = SubmitField('Submit')

class ScanImageForm(FlaskForm):
    prompt = TextAreaField('Enter the essay question', validators=[DataRequired()])
    # question_type = SelectField('Select question type',
    #     choices=[('part_a', 'Part A'), ('part_b', 'Part B')],
    #     validators=[DataRequired()]
    # )
    picture = MultipleFileField('Wrote your essay on paper? Upload the jpg or png images of your written essay:',
                                validators=[FileAllowed(['jpg', 'png']), validate_either_or])
    essay_response = TextAreaField('Enter the essay response', validators=[validate_either_or])
    submit = SubmitField('Submit')
