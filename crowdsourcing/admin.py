from __future__ import absolute_import

import re

from django.contrib import admin
from django.core.urlresolvers import reverse
from django.forms import ModelForm, ValidationError
from django.forms.widgets import Select
from django.utils.translation import ugettext_lazy as _

from .models import (Question, Survey, Answer, Submission,
                     SurveyReport, SurveyReportDisplay, OPTION_TYPE_CHOICES,
                     SURVEY_DISPLAY_TYPE_CHOICES,
                     SURVEY_AGGREGATE_TYPE_CHOICES, FORMAT_CHOICES)


try:
    from .flickrsupport import get_group_names, get_group_id
except ImportError:
    get_group_names = None

class QuestionForm(ModelForm):
    class Meta:
        model = Question

    def clean(self):
        OTC = OPTION_TYPE_CHOICES
        opts = self.cleaned_data.get('options', "")
        option_type = self.cleaned_data.get('option_type', "")
        numeric_list = option_type in (OTC.NUMERIC_SELECT, OTC.NUMERIC_CHOICE,)
        if numeric_list:
            for option in filter(None, (s.strip() for s in opts.splitlines())):
                try:
                    float(option)
                except ValueError:
                    raise ValidationError(_(
                        "For numeric select or numeric choice, all your "
                        "options must be a number. This is not a number: ") +
                        option)
        if numeric_list or option_type in (OTC.SELECT, OTC.CHOICE,):
            if not opts.splitlines():
                raise ValidationError(_(
                    "Choice type questions require a list of options."))
        return self.cleaned_data

    def clean_fieldname(self):
        fieldname = self.cleaned_data.get('fieldname', "").strip()
        if not re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', fieldname):
            raise ValidationError(_('The field name must start with a letter '
                                    'and contain nothing but alphanumerics '
                                    'and underscore.'))
        return fieldname


class QuestionInline(admin.StackedInline):
    model = Question
    extra = 3
    form = QuestionForm


def _flickr_group_choices():
    blank = [('', '------',)]
    if get_group_names:
        return blank + [(n, n,) for n in get_group_names()]
    return blank


class SurveyAdminForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super(SurveyAdminForm, self).__init__(*args, **kwargs)
        qs = SurveyReport.objects.filter(survey=self.instance)
        self.fields['default_report'].queryset = qs
        self.fields['flickr_group_name'].widget = Select(choices=_flickr_group_choices())

    class Meta:
        model = Survey

    def clean_flickr_group_name(self):
        group = self.cleaned_data.get('flickr_group_name', "")
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


def submissions_as(obj):
    return obj.get_download_tags()
submissions_as.allow_tags=True
submissions_as.short_description = 'Submissions as'


class SurveyAdmin(admin.ModelAdmin):
    save_as = True
    form = SurveyAdminForm
    search_fields = ('title', 'slug', 'tease', 'description')
    prepopulated_fields = {'slug' : ('title',)}
    list_display = (
        'title',
        'slug',
        'survey_date',
        'ends_at',
        'is_published',
        'site',
        submissions_as)
    list_filter = ('survey_date', 'is_published', 'site')
    date_hierarchy = 'survey_date'
    inlines = [QuestionInline]


admin.site.register(Survey, SurveyAdmin)


class AnswerInline(admin.TabularInline):
    model = Answer
    exclude = ('question',)
    extra = 0


class SubmissionAdmin(admin.ModelAdmin):
    raw_id_fields = ('user',)
    search_fields = ('answer__text_answer',)
    list_display = ('survey', 'submitted_at', 'user',
                    'ip_address', 'email', 'is_public',)
    list_editable = ('is_public',)
    list_filter = ('survey', 'submitted_at', 'is_public')
    date_hierarchy = 'submitted_at'
    inlines = [AnswerInline]


admin.site.register(Submission, SubmissionAdmin)


SDTC = SURVEY_DISPLAY_TYPE_CHOICES
TEXT = SDTC.TEXT
PIE = SDTC.PIE
MAP = SDTC.MAP
BAR = SDTC.BAR
LINE = SDTC.LINE
DOWNLOAD = SDTC.DOWNLOAD


class SurveyReportDisplayInlineForm(ModelForm):
    def clean(self):
        display_type = self.cleaned_data.get("display_type", "")
        aggregate_type = self.cleaned_data.get("aggregate_type", "")
        fieldnames = self.cleaned_data.get("fieldnames", "")
        x_axis_fieldname = self.cleaned_data.get("x_axis_fieldname", "")
        annotation = self.cleaned_data.get("annotation", "")
        is_chart = display_type in (BAR, LINE,)
        is_count = aggregate_type == SURVEY_AGGREGATE_TYPE_CHOICES.COUNT
        one_axis_count = is_chart and is_count
        if display_type == TEXT:
            if not annotation:
                raise ValidationError(_(
                    "Use the 'annotation' of Text Survey Report Displays to "
                    "insert arbitrary text."))
        elif not any([one_axis_count, fieldnames, display_type == DOWNLOAD]):
            raise ValidationError(_(
                "Given the options you picked, you need to specify some "
                "fieldnames or this Survey Report Display won't do "
                "anything."))
        if not is_chart and x_axis_fieldname:
            raise ValidationError(_(
                "An x axis only makes sense for Bar and Line graphs."))
        elif is_chart and not x_axis_fieldname:
            raise ValidationError(_(
                "You have to specify an x-axis for bar and line graphs."))
        if aggregate_type != SURVEY_AGGREGATE_TYPE_CHOICES.DEFAULT:
            if display_type == TEXT:
                raise ValidationError(_("Use 'Default' for Text."))
            elif display_type == PIE and not is_count:
                raise ValidationError(_(
                    "Use 'Default' or 'Count' for Pie charts."))
        return self.cleaned_data

    class Meta:
        model = SurveyReportDisplay


class SurveyReportDisplayInline(admin.StackedInline):
    form = SurveyReportDisplayInlineForm

    fieldsets = (
        (None,
            {'fields': (
                'display_type',
                'fieldnames',
                'annotation',
                'order',)}),
        ('Pie, Line, and Bar Charts',
            {'fields': (
                'aggregate_type',
                'x_axis_fieldname',)}),
        ('Slideshow',
            {'fields': ('caption_fields',)}),
        ('Maps',
            {'fields': (
                'limit_map_answers',
                'map_center_latitude',
                'map_center_longitude',
                'map_zoom',)}))

    model = SurveyReportDisplay
    extra = 3


class SurveyReportAdmin(admin.ModelAdmin):
    list_display = ('__unicode__', 'slug', 'survey',)
    prepopulated_fields = {'slug': ('title',)}
    inlines = [SurveyReportDisplayInline]


admin.site.register(SurveyReport, SurveyReportAdmin)
