from __future__ import absolute_import

import re

from django.contrib import admin
from django.forms import ModelForm, ValidationError
from django.utils.translation import ugettext_lazy as _

from .models import (Question, Survey, Answer, Submission,
                     SurveyReport, SurveyReportDisplay)

try:
    from .flickrsupport import get_group_names, get_group_id
except ImportError:
    get_group_names = None

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
    model = Question
    extra = 3
    form = QuestionForm


class SurveyAdminForm(ModelForm):
    class Meta:
        model = Survey

    def clean_flickr_group_name(self):
        group = self.cleaned_data['flickr_group_name']
        if group:
            if not get_group_names:
                raise ValidationError(
                    _("Flickr support is broken. Contact a programmer."))
            elif not get_group_id(group):
                names = ", ".join(get_group_names())
                if names:
                    args = (group, names)
                    raise ValidationError(
                        _("You can't access this group: %s. Either the group "
                          "doesn't exist, or you don't have permission. You "
                          "have permission to these groups: %s") % args)
                else:
                    raise ValidationError(
                        _("You can't access any Flickr groups. Either you "
                          "don't have any groups or your configuration "
                          "settings are incorrect and you need to contact a "
                          "programmer."))
        return group


class SurveyAdmin(admin.ModelAdmin):
    form = SurveyAdminForm
    search_fields = ('title', 'slug', 'tease', 'description')
    prepopulated_fields = {'slug' : ('title',)}
    list_display = (
        'title',
        'slug',
        'survey_date',
        'ends_at',
        'is_published',
        'site')
    list_filter = ('survey_date', 'is_published', 'site')
    date_hierarchy = 'survey_date'
    inlines = [QuestionInline]


admin.site.register(Survey, SurveyAdmin)


class AnswerInline(admin.TabularInline):
    model = Answer
    exclude = ('question',)
    extra = 0


class SubmissionAdmin(admin.ModelAdmin):
    search_fields = ('answer__text_answer',) #'title', 'story', 'address')
    list_display = ('survey', 'submitted_at', 'user',
                    'ip_address', 'email', 'is_public',)
    list_editable = ('is_public',)
    list_filter = ('survey', 'submitted_at', 'is_public')
    date_hierarchy = 'submitted_at'
    inlines = [AnswerInline]


admin.site.register(Submission, SubmissionAdmin)


class SurveyReportDisplayInline(admin.StackedInline):
    model = SurveyReportDisplay
    extra = 3


class SurveyReportAdmin(admin.ModelAdmin):
    inlines = [SurveyReportDisplayInline]


admin.site.register(SurveyReport, SurveyReportAdmin)    
