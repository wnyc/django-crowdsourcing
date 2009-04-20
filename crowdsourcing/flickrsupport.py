"""
support for mirroring submitted photos on Flickr.

"""
from __future__ import absolute_import

import flickrapi

from . import settings as local_settings


_flickr=None


def _get_flickr():
    global _flickr
    if not _flickr:
        _flickr=flickrapi.FlickrAPI(local_settings.FLICKR_API_KEY, local_settings.FLICKR_API_SECRET)
        _flickr.get_token_part_two((local_settings.FLICKR_TOKEN, local_settings.FLICKR_FROB))
    return _flickr


def get_photo_hash(djfile):
    h=hashlib.sha1()
    for chunk in djfile.chunks():
        h.update(chunk)
    return h.hexdigest()


def flickr_add_to_pool(photo_id, group_id):
    flickr=_get_flickr()
    flickr.groups_pools_add(photo_id=photo_id,
                            group_id=group_id)
        

def sync_to_flickr(answer, pool_id):
    
    flickr=_get_flickr()
            
    if (not answer.flickr_id) and answer.image_answer:
        
        answer.photo_hash=get_photo_hash(answer.image_answer)
        
        res=flickr.upload(filename=answer.image_answer.path.encode('utf-8'),
                          title=c.title.encode('utf-8'),
                          is_public='1' if local_settings.FLICKR_LIVE else '0',
                          )
                
        photo_id=res.findtext('photoid')
        if photo_id and pool_id:
            answer.flickr_id=photo_id
            flickr.groups_pools_add(photo_id=photo_id, group_id=pool_id)
    else:
        if not answer.image_answer:
            if answer.flickr_id:
                res=flickr.photos_delete(photo_id=answer.flickr_id)
                answer.flickr_id=''
            answer.photo_hash=''
        else:
            assert answer.flickr_id
            new_hash=get_photo_hash(answer.image_answer)
            if new_hash == answer.photo_hash:
                # nothing changed
                return
            else:
                answer.photo_hash=new_hash

                res=flickr.replace(filename=answer.image_answer.path,
                                   photo_id=answer.flickr_id,
                                   format='etree')
                photo_id=res.findtext('photoid')
                answer.flickr_id=photo_id
    return answer
    

