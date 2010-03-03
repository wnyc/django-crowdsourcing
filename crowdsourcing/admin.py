from __future__ import absolute_import

import re

from django.contrib import admin
from django.forms import ModelForm, ValidationError
from django.utils.translation import ugettext_lazy as _

from .models import Question, Survey, Answer, Submission, SurveyGroup


class QuestionForm(ModelForm):
    class Meta:
        model = Question

    def clean_fieldname(self):
        fieldname = self.cleaned_data['fieldname'].strip()
        if not re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', fieldname):
            raise ValidationError(_('The field name must start with a letter '
                                    'and contain nothing but alphanumerics '
                                    'and underscore.'))
        return fieldname


class QuestionInline(admin.StackedInline):
    model=Question
    extra=1
    form=QuestionForm


class SurveyAdmin(admin.ModelAdmin):
    search_fields = ('title', 'slug', 'tease', 'description')
    prepopulated_fields = {'slug' : ('title',)}
    list_display = (
        'title',
        'survey_date',
        'ends_at',
        'is_published',
        'survey_group')
    list_filter = ('survey_date', 'is_published')
    date_hierarchy = 'survey_date'
    inlines = [QuestionInline]


class AnswerInline(admin.TabularInline):
    model=Answer
    exclude=('question',)
    extra=0


class SubmissionAdmin(admin.ModelAdmin):
    search_fields=('answer__text_answer',) #'title', 'story', 'address')
    list_display=('survey', 'submitted_at', 'user',
                  'ip_address', 'email', 'is_public',)
    list_editable=('is_public',)
    list_filter=('survey', 'submitted_at', 'is_public')
    date_hierarchy='submitted_at'
    inlines=[AnswerInline]


admin.site.register(Survey, SurveyAdmin)
admin.site.register(Submission, SubmissionAdmin)

