try:
    from sorl.thumbnail.fields import ImageField, ImageFormField
    from sorl.thumbnail.shortcuts import get_thumbnail
except ImportError:
    from django.db.models import ImageField
from . import settings as local_settings
