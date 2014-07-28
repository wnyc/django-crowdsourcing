try:
    from sorl.thumbnail.fields import ImageField
except ImportError:
    from django.db.models import ImageField

class ImageWithThumbnailsField(ImageField):
    def __init__(self, *args, **kwargs):
        kwargs.pop('thumbnail', None)
        kwargs.pop('extra_thumbnails', None)
        super(ImageWithThumbnailsField, self).__init__(*args, **kwargs)

    @property
    def extra_thumbnails(self):
        return dict()

    @property
    def extra_thumbnails_tag(self):
        return dict()

    def to_python(self, *args, **kwargs):
        res = super(ImageWithThumbnailsField, self).to_python(*args, **kwargs)
        import pdb; pdb.set_trace()
        setattr(res, 'thumbnail', dict())
        return res
