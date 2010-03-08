from __future__ import absolute_import

from django.conf.urls.defaults import patterns, url

from .views import (allowed_actions,
                    questions,
                    survey_detail,
                    survey_report)

urlpatterns=patterns(
    "",
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
