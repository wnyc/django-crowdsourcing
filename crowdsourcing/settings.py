from django.conf import settings as _gs

MODERATE_SUBMISSIONS=getattr(_gs, 'CROWDSOURCING_MODERATE_SUBMISSIONS', False)
