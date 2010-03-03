from __future__ import absolute_import

import re

from django.conf import settings
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
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _

from .geo import get_latitude_and_longitude
from .models import OPTION_TYPE_CHOICES, Answer, Survey, Question, Submission
from .settings import VIDEO_URL_PATTERNS, IMAGE_UPLOAD_PATTERN


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
            print self, self.submission, ans
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
        if value and not any(re.match(v, value) for v in VIDEO_URL_PATTERNS):
            raise ValidationError(_("A video url is required."))
        return value


class PhotoUpload(BaseAnswerForm):
    answer = ImageField()

##     def clean_answer(self):
##         value=self.cleaned_data['answer']
##         if value:
##             mediaroot=settings.MEDIA_ROOT
##             subpath=datetime.datetime.now().strftime(IMAGE_UPLOAD_PATTERN)
##             dirpath=os.path.join(mediaroot, subpath)
##             if not os.path.exists(dirpath):
##                 os.makedirs(dirpath)
##             dest=os.path.join(subpath, value.name)
##             fullpath=os.path.join(mediaroot, dest)
##             while os.path.exists(fullpath):
##                 dest+='_'
##                 fullpath=os.path.join(mediaroot, dest)
##             with open(fullpath, 'wb+') as fp:
##                 for chunk in value.chunks():
##                     fp.write(chunk)
##             return dest
##         return value


class LocationAnswer(BaseAnswerForm):
    answer = CharField()

    def save(self, commit=True):
        obj = super(LocationAnswer, self).save(commit=False)
        obj.latitude, obj.longitude = get_latitude_and_longitude(obj.value)
        if commit:
            obj.save()
        return obj
        

class BaseOptionAnswer(BaseAnswerForm):
    def __init__(self, *args, **kwargs):
        super(BaseOptionAnswer, self).__init__(*args, **kwargs)
        choices = [(x, x) for x in self.question.parsed_options]
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


## each question gets a form with one element, determined by the type
## for the answer.
QTYPE_FORM = {
    OPTION_TYPE_CHOICES.TEXT_FIELD:        TextInputAnswer,
    OPTION_TYPE_CHOICES.INTEGER:           IntegerInputAnswer,
    OPTION_TYPE_CHOICES.FLOAT:             FloatInputAnswer,
    OPTION_TYPE_CHOICES.BOOLEAN:           BooleanInputAnswer,
    OPTION_TYPE_CHOICES.TEXT_AREA:         TextAreaAnswer,
    OPTION_TYPE_CHOICES.SELECT_ONE_CHOICE: OptionAnswer,
    OPTION_TYPE_CHOICES.RADIO_LIST:        OptionRadio,
    OPTION_TYPE_CHOICES.CHECKBOX_LIST:     OptionCheckbox,
    OPTION_TYPE_CHOICES.EMAIL_FIELD:       EmailAnswer, 
    OPTION_TYPE_CHOICES.PHOTO_UPLOAD:      PhotoUpload,
    OPTION_TYPE_CHOICES.VIDEO_LINK:        VideoAnswer,
    OPTION_TYPE_CHOICES.LOCATION_FIELD:    LocationAnswer,
}


class SubmissionForm(ModelForm):

    def __init__(self, survey, *args, **kwargs):
        super(SubmissionForm, self).__init__(*args, **kwargs)
        self.survey = survey
        
    class Meta:
        model = Submission
        exclude = ('survey', 'submitted_at','ip_address','user', 'is_public')


def forms_for_survey(survey, request, submission=None):
    session_key = request.session.session_key.lower()
    posted_data = request.POST or None
    files = request.FILES or None
    main_form = SubmissionForm(survey, data=posted_data, files=files)
    return [main_form] + [
        QTYPE_FORM[q.option_type](question=q,
                                  session_key=session_key,
                                  submission=submission,
                                  prefix='%s_%s' % (survey.id, q.id),
                                  data=posted_data,
                                  files=files)
        for q in survey.questions.all().order_by("order")]
