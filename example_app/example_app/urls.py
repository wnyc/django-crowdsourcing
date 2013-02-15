from django.conf import settings
from django.conf.urls.defaults import *
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    ('', include('cms.urls')),
    (r'^crowdsourcing/', include('crowdsourcing.urls')),
    # Uncomment the admin/doc line below and add 'django.contrib.admindocs' 
    # to INSTALLED_APPS to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),
    (r'^admin/', include(admin.site.urls)),
    (r'^media/(?P<path>.*)$',
     'django.views.static.serve',
     {'document_root': settings.MEDIA_ROOT}),
    # See settings.py for detailed instructions on how to build the
    # documentation.
    (r'^docs/(?P<path>.*)$',
     'django.views.static.serve',
     {'document_root': settings.DOCUMENTATION_ROOT})
)
