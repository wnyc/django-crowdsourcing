from __future__ import absolute_import

from django.conf.urls.defaults import patterns, url

from .views import (aggregate_results,
                    can_enter,
                    questions,
                    survey_detail,
                    survey_results,
                    survey_results_json,
                    survey_results_map,
                    survey_results_archive,
                    survey_results_aggregate)

urlpatterns=patterns(
    "",
    url(r'^(?P<slug>[-a-z0-9_]+)/$',
        survey_detail,
        name="survey_detail"),

    url(r'^(?P<slug>[-a-z0-9_]+)/results/$',
        survey_results,
        name="survey_results"),

    url(r'^(?P<slug>[-a-z0-9_]+)/results/map/$',
        survey_results_map,
        name="survey_results_map"),

    url(r'^(?P<slug>[-a-z0-9_]+)/results/archive/$',
        survey_results_archive,
        name="survey_results_archive"),

    url(r'^(?P<slug>[-a-z0-9_]+)/results/aggregate/$',
        survey_results_aggregate,
        name="survey_results_aggregate"),

    url(r'^(?P<slug>[-a-z0-9_]+)/api/$',
        survey_results_json,
        name="survey_results_api"),

    url(r'^(?P<slug>[-a-z0-9_]+)/api/can_enter/$',
        can_enter,
        name="can_enter"),

    url(r'^(?P<slug>[-a-z0-9_]+)/api/questions/$',
        questions,
        name="questions"),
    
    url(r'^(?P<slug>[-a-z0-9_]+)/api/aggregate_results/$',
        aggregate_results,
        name="aggregate_results"),
    )

