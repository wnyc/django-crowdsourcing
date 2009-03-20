from __future__ import absolute_import

from itertools import chain
import logging
import uuid

from django.conf import settings
from django.forms import BaseForm, Form, ValidationError
from django.forms import CharField, IntegerField, DecimalField, ChoiceField, SplitDateTimeField,\
                            CheckboxInput, BooleanField,FileInput,\
                            FileField, ImageField, FloatField
from django.forms import Textarea, TextInput, Select, RadioSelect,\
                            CheckboxSelectMultiple, MultipleChoiceField,\
                            SplitDateTimeWidget,MultiWidget, MultiValueField
from django.forms.formsets import BaseFormSet

from django.forms.forms import BoundField
from django.forms.models import ModelForm
from django.utils.translation import ugettext_lazy as _
from django.utils.safestring import mark_safe
from django.template import Context, loader
from django.template.defaultfilters import slugify

from .models import OPTION_TYPE_CHOICES, Answer, Survey, Question, Submission

class BaseAnswerForm(Form):
    def __init__(self, question, session_key, submission=None, *args, **kwargs):
        self.question=question
        self.session_key=session_key.lower()
        if submission:
            self.user=submission.user
        else:
            self.user=None
        self.submission=submission
        super(BaseAnswerForm, self).__init__(*args, **kwargs)
        self._configure_answer_field()


    def _configure_answer_field(self):
        answer=self.fields['answer']
        answer.required=question.required
        answer.label=question.question
        answer.help_text=question.help_text        
        # set some property on the basis of question.fieldname? TBD
        return answer

    def as_template(self):
        "Helper function for fieldsting fields data from form."
        bound_fields=[BoundField(self, field, name) for name, field in self.fields.items()]
        c=Context(dict(form=self, bound_fields=bound_fields))
        t=loader.get_template('forms/form.html')
        return t.render(c)

    def save(self, commit=True):
        if not self.cleaned_data['answer']:
            if self.fields['answer'].required:
                raise ValidationError, _('This field is required.')
            return
        ans=Answer()
        ans.submission=self.submission
        ans.question=self.question
        ans.value=self.cleaned_data['answer']
        if commit:
            ans.save()
        return ans

class TextInputAnswer(BaseAnswerForm):
    answer=CharField()

class IntegerInputAnswer(BaseAnswerForm):
    answer=IntegerField()
    
class FloatInputAnswer(BaseAnswerForm):
    answer=FloatField()
    
class BooleanInputAnswer(BaseAnswerForm):
    answer=BooleanField(required=False)

    def _configure_answer_field(self):
        fld=super(BooleanInputAnswer, self)._configure_answer_field()
        # we don't want to set this as required, as a single boolean field
        # being required doesn't make much sense in a survey
        fld.required=False
        return fld
        
class TextAreaAnswer(BaseAnswerForm):
    answer=CharField(widget=Textarea)

class NullSelect(Select):
    def __init__(self, attrs=None, choices=(), empty_label=u"---------"):
        self.empty_label=empty_label
        super(NullSelect, self).__init__(attrs, choices)

    def render(self, name, value, attrs=None, choices=(), **kwargs):
        empty_choice=()
        # kwargs is needed because it is the only way to determine if an
        # override is provided or not.
        if 'empty_label' in kwargs:
            if kwargs['empty_label'] is not None:
                empty_choice=((u'', kwargs['empty_label']),)
        elif self.empty_label is not None:
            empty_choice=((u'', self.empty_label),)
        base_choices=self.choices
        self.choices=chain(empty_choice, base_choices)
        result=super(NullSelect, self).render(name, value, attrs, choices)
        self.choices=base_choices
        return result


class BaseOptionAnswer(BaseAnswerForm):
    def __init__(self, *args, **kwargs):
        super(BaseOptionAnswer, self).__init__(*args, **kwargs)
        self.fields['answer'].choices=[(x,x) for x in self.question.parsed_options]
        
    def clean_answer(self):
        key=self.cleaned_data['answer']
        if not key and self.fields['answer'].required:
            raise ValidationError, _('This field is required.')
        return key
    
    def save(self, commit=True):
        for text in self.cleaned_data['answer']:
            ans=Answer()
            ans.submission=self.submission
            ans.question=self.question
            ans.value=text
            if commit:
                ans.save()
            ans_list.append(ans)
        return ans_list

class OptionAnswer(BaseOptionAnswer):
    answer=ChoiceField(widget=NullSelect)


class OptionRadio(BaseOptionAnswer):
    def __init__(self, *args, **kwargs):
        super(OptionRadio, self).__init__(*args, **kwargs)
        self.fields['answer'].widget=RadioSelect(choices=self.choices)

class OptionCheckbox(BaseOptionAnswer):
    answer=MultipleChoiceField(widget=CheckboxSelectMultiple)


## each question gets a form with one element, determined by the type
## for the answer.
QTYPE_FORM={
    OPTION_TYPE_CHOICES.TEXT_FIELD:        TextInputAnswer,
    OPTION_TYPE_CHOICES.INTEGER:           IntegerInputAnswer,
    OPTION_TYPE_CHOICES.FLOAT:             FloatInputAnswer,
    OPTION_TYPE_CHOICES.BOOLEAN:           BooleanInputAnswer,
    OPTION_TYPE_CHOICES.TEXT_AREA:         TextAreaAnswer,
    OPTION_TYPE_CHOICES.SELECT_ONE_CHOICE: OptionAnswer,
    OPTION_TYPE_CHOICES.RADIO_LIST:        OptionRadio,
    OPTION_TYPE_CHOICES.CHECKBOX_LIST:     OptionCheckbox,
}

class SubmissionForm(ModelForm):
    class Meta:
        model=Submission
        exclude=('survey','latitude', 'longitude','submitted_at','ip_address','user',)

def forms_for_survey(survey, request, submission=None):
    sp=str(survey.id) + '_'
    session_key=request.session.session_key.lower()
    login_user=request.user
    posted_data=request.POST or None
    files=request.FILES or None
    main_form=SubmissionForm(posted_data, files)
    return [main_form] + [
        QTYPE_FORM[q.option_type](q, session_key, submission=submission, prefix=sp+str(q.id), data=posted_data)
        for q in survey.questions.all().order_by("order")]


