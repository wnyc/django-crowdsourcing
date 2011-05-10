from __future__ import absolute_import

from django.conf.urls.defaults import patterns, url

from .views import (allowed_actions,
                    embeded_survey_questions,
                    embeded_survey_report,
                    location_question_results,
                    location_question_map,
                    questions,
                    submissions,
                    submission,
                    submission_for_map,
                    survey_detail,
                    survey_report)

urlpatterns = patterns(
    "",
    url(r'^submissions/$',
        submissions,
        {"format": "json"},
        name='submissions'),

    url(r'^submissions/(?P<format>[a-z]+)/$',
        submissions,
        name='submissions_by_format'),

    url(r'^submission/(?P<id>\d+)/$',
        submission),

    url(r'^submission_for_map/(?P<id>\d+)/$',
        submission_for_map),

    url(r'^location_question_results/(?P<question_id>\d+)/(?P<limit_map_answers>\d+)/$',
        location_question_results,
        kwargs={"survey_report_slug": ""}),

    url(r'^location_question_results/(?P<question_id>\d+)/(?P<limit_map_answers>\d*)/(?P<survey_report_slug>[-a-z0-9_]*)/$',
        location_question_results,
        name="location_question_results"),

    url(r'^location_question_map/(?P<question_id>\d+)/(?P<display_id>\d+)/$',
        location_question_map,
        name="location_question_map"),

    url(r'^location_question_map/(?P<question_id>\d+)/(?P<display_id>\d+)/(?P<survey_report_slug>[-a-z0-9_]*)/$',
        location_question_map,
        name="location_question_map"),

    url(r'^(?P<slug>[-a-z0-9_]+)/$',
        survey_detail,
        name="survey_detail"),

    url(r'^(?P<slug>[-a-z0-9_]+)/api/allowed_actions/$',
        allowed_actions,
        name="allowed_actions"),

    url(r'^(?P<slug>[-a-z0-9_]+)/api/questions/$',
        questions,
        name="questions"),

    url(r'^(?P<slug>[-a-z0-9_]+)/api/embeded_survey_questions/$',
        embeded_survey_questions,
        name="embeded_survey_questions"),

    url(r'^(?P<slug>[-a-z0-9_]+)/api/report/$',
        embeded_survey_report,
        {"report": ""},
        name="embeded_survey_report_default"),

    url(r'^(?P<slug>[-a-z0-9_]+)/api/report/(?P<report>[-a-z0-9_]+)/$',
        embeded_survey_report,
        name="embeded_survey_report"),

    url(r'^(?P<slug>[-a-z0-9_]+)/report/$',
        survey_report,
        name="survey_default_report_page_1"),

    url(r'^(?P<slug>[-a-z0-9_]+)/report/(?P<page>\d+)/$',
        survey_report,
        name="survey_default_report"),

    url(r'^(?P<slug>[-a-z0-9_]+)/(?P<report>[-a-z0-9_]+)/$',
        survey_report,
        name="survey_report_page_1"),

    url(r'^(?P<slug>[-a-z0-9_]+)/(?P<report>[-a-z0-9_]+)/(?P<page>\d+)/$',
        survey_report,
        name="survey_report")
    )
