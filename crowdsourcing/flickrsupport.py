"""
support for mirroring submitted photos on Flickr.
"""
from __future__ import absolute_import
import logging
from urllib2 import URLError

from django.core.cache import cache

import flickrapi
import hashlib

from . import settings as local_settings


_flickr = None


def _has_flickr():
    return all([local_settings.FLICKR_API_KEY,
                local_settings.FLICKR_API_SECRET,
                local_settings.FLICKR_TOKEN])

def _get_flickr():
    global _flickr
    if not _flickr and _has_flickr():
        _flickr = flickrapi.FlickrAPI(local_settings.FLICKR_API_KEY,
                                      local_settings.FLICKR_API_SECRET,
                                      token=local_settings.FLICKR_TOKEN)
    return _flickr


def get_photo_hash(djfile):
    h = hashlib.sha1()
    for chunk in djfile.chunks():
        h.update(chunk)
    return h.hexdigest()


def _get_groups():
    flickr = _get_flickr()
    if flickr:
        key = "flickr_groups"
        groups = cache.get(key, None)
        if not groups:
            try:
                groups = flickr.groups_pools_getGroups()._children[0]._children
            except (URLError, flickrapi.FlickrError) as ex:
                logging.exception("Flick error retrieving groups: %s", str(ex))
                groups = []
            cache.set(key, groups)
        return groups
    return []


def get_group_names():
    return [group.get("name") for group in _get_groups()]


def get_group_id(group_name):
    if group_name:
        for group in _get_groups():
            if group.get("name") == group_name:
                return group.get("id")
    return ""


def sync_to_flickr(answer, group_id):
    flickr = _get_flickr()

    if (not answer.flickr_id) and answer.image_answer:
        answer.photo_hash = get_photo_hash(answer.image_answer)

        filename = answer.image_answer.path.encode('utf-8')
        title = filename.split("/")[-1] # Should we do something fancier here?
        res = flickr.upload(
            filename = filename,
            title = title,
            is_public = '1' if local_settings.FLICKR_LIVE else '0')

        photo_id = res.findtext('photoid')
        if photo_id and group_id:
            answer.flickr_id = photo_id
            flickr.groups_pools_add(photo_id=photo_id, group_id=group_id)
    else:
        if not answer.image_answer:
            if answer.flickr_id:
                res = flickr.photos_delete(photo_id=answer.flickr_id)
                answer.flickr_id = ''
            answer.photo_hash = ''
        else:
            assert answer.flickr_id
            new_hash = get_photo_hash(answer.image_answer)
            if new_hash == answer.photo_hash:
                # nothing changed
                return
            else:
                answer.photo_hash = new_hash

                res = flickr.replace(filename=answer.image_answer.path,
                                   photo_id=answer.flickr_id,
                                   format='etree')
                photo_id = res.findtext('photoid')
                answer.flickr_id = photo_id
    return answer
