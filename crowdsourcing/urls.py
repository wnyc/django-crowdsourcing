from __future__ import absolute_import

from django.conf.urls.defaults import patterns, url

from .views import survey_detail, survey_results

urlpatterns=patterns(
    "",
    url(r'^(?P<slug>[-a-z0-9_]+)/$',
        survey_detail,
        name="survey_detail"),

    url(r'^(?P<slug>[-a-z0-9_]+)/results/$',
        survey_results,
        name="survey_results"),

    )

