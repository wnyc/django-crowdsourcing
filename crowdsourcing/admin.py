from __future__ import absolute_import

from django.contrib import admin

from .models import Question, Survey, Answer, Submission

class QuestionInline(admin.StackedInline):
    model=Question
    extra=1

class SurveyAdmin(admin.ModelAdmin):
    search_fields=('title', 'slug', 'tease', 'description')
    prepopulated_fields={'slug' : ('title',)}
    list_display=('title', 'survey_date', 'ends_at', 'is_published')
    list_filter=('survey_date', 'is_published')
    date_hierarchy='survey_date'
    inlines=[QuestionInline]

class AnswerInline(admin.TabularInline):
    model=Answer
    extra=0

class SubmissionAdmin(admin.ModelAdmin):
    search_fields=('email', 'title', 'story', 'address')
    list_display=('survey', 'submitted_at', 'user', 'email', 'ip_address', 'title', 'is_public')
    list_filter=('survey', 'submitted_at', 'is_public')
    date_hierarchy='submitted_at'
    inlines=[AnswerInline]

admin.site.register(Survey, SurveyAdmin)
admin.site.register(Submission, SubmissionAdmin)
