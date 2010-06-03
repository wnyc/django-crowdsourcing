from __future__ import absolute_import

from django.conf.urls.defaults import patterns, url

from .views import (allowed_actions,
                    location_question_results,
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
        name='submissions'),

    url(r'^submission/(?P<id>\d+)/$',
        submission),

    url(r'^submission_for_map/(?P<id>\d+)/$',
        submission_for_map),

    url(r'^location_question_results/(?P<question_id>\d+)/ids/(?P<submission_ids>[0-9,]+)/$',
        location_question_results,
        {"limit_map_answers": None},
        name="location_question_results_ids"),

    url(r'^location_question_results/(?P<question_id>\d+)/limit/(?P<limit_map_answers>\d+)/$',
        location_question_results,
        {"submission_ids": None},
        name="location_question_results_limit"),

    url(r'^location_question_results/(?P<question_id>\d+)/$',
        location_question_results,
        {"submission_ids": None, "limit_map_answers": None},
        name="location_question_results"),

    url(r'^(?P<slug>[-a-z0-9_]+)/$',
        survey_detail,
        name="survey_detail"),

    url(r'^(?P<slug>[-a-z0-9_]+)/api/allowed_actions/$',
        allowed_actions,
        name="allowed_actions"),

    url(r'^(?P<slug>[-a-z0-9_]+)/api/questions/$',
        questions,
        name="questions"),
    
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
