from __future__ import absolute_import

import re

from django.conf import settings
from django.core.files.images import get_image_dimensions
from django.forms import (
    BooleanField,
    CharField,
    CheckboxSelectMultiple,
    ChoiceField,
    EmailField,
    FloatField,
    Form,
    ImageField,
    IntegerField,
    MultipleChoiceField,
    RadioSelect,
    Select,
    Textarea,
    ValidationError,
    )
from django.forms.forms import BoundField
from django.forms.formsets import BaseFormSet
from django.forms.models import ModelForm
from django.template import Context, loader
from django.template.defaultfilters import slugify
from django.utils.html import strip_tags
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _

from .geo import get_latitude_and_longitude
from .models import OPTION_TYPE_CHOICES, Answer, Survey, Question, Submission
from .settings import VIDEO_URL_PATTERNS, IMAGE_UPLOAD_PATTERN

try:
    from .oembedutils import oembed_expand
except ImportError:
    oembed_expand = None


class BaseAnswerForm(Form):
    def __init__(self,
                 question,
                 session_key,
                 submission=None,
                 *args,
                 **kwargs):
        self.question = question
        self.session_key = session_key
        self.submission = submission
        super(BaseAnswerForm, self).__init__(*args, **kwargs)
        self._configure_answer_field()

    def _configure_answer_field(self):
        answer = self.fields['answer']
        q = self.question
        answer.required = q.required
        answer.label = q.question
        answer.help_text = q.help_text
        # set some property on the basis of question.fieldname? TBD
        return answer

    def as_template(self):
        "Helper function for fieldsting fields data from form."
        bound_fields = [BoundField(self, field, name) \
                      for name, field in self.fields.items()]
        c = Context(dict(form=self, bound_fields=bound_fields))
        t = loader.get_template('forms/form.html')
        return t.render(c)

    def save(self, commit=True):
        if self.cleaned_data['answer'] is None:
            if self.fields['answer'].required:
                raise ValidationError, _('This field is required.')
            return
        ans = Answer()
        if self.submission:
            ans.submission = self.submission
        ans.question = self.question
        ans.value = self.cleaned_data['answer']
        if commit:
            ans.save()
        return ans


class TextInputAnswer(BaseAnswerForm):
    answer = CharField()


class IntegerInputAnswer(BaseAnswerForm):
    answer = IntegerField()


class FloatInputAnswer(BaseAnswerForm):
    answer = FloatField()


class BooleanInputAnswer(BaseAnswerForm):
    answer = BooleanField(initial=False)

    def clean_answer(self):
        value = self.cleaned_data['answer']
        if not value:
            return False
        return value

    def _configure_answer_field(self):
        fld = super(BooleanInputAnswer, self)._configure_answer_field()
        # we don't want to set this as required, as a single boolean field
        # being required doesn't make much sense in a survey
        fld.required = False
        return fld


class TextAreaAnswer(BaseAnswerForm):
    answer = CharField(widget=Textarea)


class EmailAnswer(BaseAnswerForm):
    answer = EmailField()


class VideoAnswer(BaseAnswerForm):
    answer = CharField()

    def clean_answer(self):
        value = self.cleaned_data['answer']
        if value:
            if oembed_expand:
                if oembed_expand(value):
                    return value
                else:
                    print "Couldn't expand %s" % value
            else:
                matches = [re.match(v, value) for v in VIDEO_URL_PATTERNS]
                first_match = reduce(lambda x, y: x or y, matches)
                if first_match:
                    return first_match.group(0)
            raise ValidationError(_(
                "I don't recognize this video url format. Try something like "
                "http://www.youtube.com/watch?v=Bfli1yuby58."))
        return value


class PhotoUpload(BaseAnswerForm):
    answer = ImageField()

    def clean_answer(self):
        answer = self.cleaned_data['answer']
        if answer and not get_image_dimensions(answer.file):
            raise ValidationError(_(
                "We couldn't read your file. Make sure it's a .jpeg, .png, or "
                ".gif file, not a .psd or other unsupported type."))
        return answer


class LocationAnswer(BaseAnswerForm):
    answer = CharField()

    def save(self, commit=True):
        obj = super(LocationAnswer, self).save(commit=False)
        if obj.value:
            obj.latitude, obj.longitude = get_latitude_and_longitude(obj.value)
            if commit:
                obj.save()
            return obj
        return None


class BaseOptionAnswer(BaseAnswerForm):
    def __init__(self, *args, **kwargs):
        super(BaseOptionAnswer, self).__init__(*args, **kwargs)
        options = self.question.parsed_options
        # appendChoiceButtons in survey.js duplicates this. jQuery and django
        # use " for html attributes, so " will mess them up.
        choices = []
        for x in options:
            choices.append(
                (strip_tags(x).replace('&amp;', '&').replace('"', "'").strip(),
                 mark_safe(x)))
        if not self.question.required and not isinstance(self, OptionCheckbox):
            choices = [('', '---------',)] + choices
        self.fields['answer'].choices = choices

    def clean_answer(self):
        key = self.cleaned_data['answer']
        if not key and self.fields['answer'].required:
            raise ValidationError, _('This field is required.')
        if not isinstance(key, (list, tuple)):
            key = (key,)
        return key

    def save(self, commit=True):
        ans_list = []
        for text in self.cleaned_data['answer']:
            ans = Answer()
            if self.submission:
                ans.submission = self.submission
            ans.question = self.question
            ans.value = text
            if commit:
                ans.save()
            ans_list.append(ans)
        return ans_list


class OptionAnswer(BaseOptionAnswer):
    answer = ChoiceField()


class OptionRadio(BaseOptionAnswer):
    answer = ChoiceField(widget=RadioSelect)


class OptionCheckbox(BaseOptionAnswer):
    answer = MultipleChoiceField(widget=CheckboxSelectMultiple)


# Each question gets a form with one element determined by the type for the
# answer.
QTYPE_FORM = {
    OPTION_TYPE_CHOICES.CHAR: TextInputAnswer,
    OPTION_TYPE_CHOICES.INTEGER: IntegerInputAnswer,
    OPTION_TYPE_CHOICES.FLOAT: FloatInputAnswer,
    OPTION_TYPE_CHOICES.BOOL: BooleanInputAnswer,
    OPTION_TYPE_CHOICES.TEXT: TextAreaAnswer,
    OPTION_TYPE_CHOICES.SELECT: OptionAnswer,
    OPTION_TYPE_CHOICES.CHOICE: OptionRadio,
    OPTION_TYPE_CHOICES.NUMERIC_SELECT: OptionAnswer,
    OPTION_TYPE_CHOICES.NUMERIC_CHOICE: OptionRadio,
    OPTION_TYPE_CHOICES.BOOL_LIST: OptionCheckbox,
    OPTION_TYPE_CHOICES.EMAIL: EmailAnswer,
    OPTION_TYPE_CHOICES.PHOTO: PhotoUpload,
    OPTION_TYPE_CHOICES.VIDEO: VideoAnswer,
    OPTION_TYPE_CHOICES.LOCATION: LocationAnswer,
}


class SubmissionForm(ModelForm):

    def __init__(self, survey, *args, **kwargs):
        super(SubmissionForm, self).__init__(*args, **kwargs)
        self.survey = survey

    class Meta:
        model = Submission
        exclude = (
            'survey',
            'submitted_at',
            'ip_address',
            'user',
            'is_public',
            'featured')


def forms_for_survey(survey, request='testing', submission=None):
    testing = 'testing' == request
    session_key = "" if testing else request.session.session_key.lower()
    post = None if testing else request.POST or None
    files = None if testing else request.FILES or None
    main_form = SubmissionForm(survey, data=post, files=files)
    return [main_form] + [
        _form_for_question(q, session_key, submission, post, files)
        for q in survey.questions.all().order_by("order")]


def _form_for_question(question,
                       session_key="",
                       submission=None,
                       data=None,
                       files=None):
    return QTYPE_FORM[question.option_type](
        question=question,
        session_key=session_key,
        submission=submission,
        prefix='%s_%s' % (question.survey.id, question.id),
        data=data,
        files=files)
