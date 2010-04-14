from __future__ import absolute_import

from django.conf.urls.defaults import patterns, url

from .views import home

urlpatterns = patterns(
    "",
    url(r'^$', home)
    )
