"""
configuration and routines for dealing with oembed.

The configuration is extracted from django-oembed's initial_data.json fixture.

This code uses python-oembed with a patch to permit true regex input.
"""
import re
import urllib2

import oembed

config = [
    {
    "regex": "http://(?:www\\.)?flickr\\.com/photos/\\S+?/(?:sets/)?\\d+/?", 
    "endpoint": "http://www.flickr.com/services/oembed/", 
    "name": "Flickr"
    }, 
    {
    "regex": "http://\\S*?viddler.com/\\S*", 
    "endpoint": "http://lab.viddler.com/services/oembed/", 
    "name": "Viddler"
    }, 
    {
    "regex": "http://qik.com/\\S*", 
    "endpoint": "http://qik.com/api/oembed.json", 
    "name": "Qik"
    }, 
    {
    "regex": "http://\\S*?revision3.com/\\S*", 
    "endpoint": "http://revision3.com/api/oembed/", 
    "name": "Revision3"
    }, 
    {
    "regex": "http://\\S*.amazon.(com|co.uk|de|ca|jp)/\\S*/(gp/product|o/ASIN|obidos/ASIN|dp)/\\S*", 
    "endpoint": "http://oohembed.com/oohembed/", 
    "name": "Amazon Product Image (OohEmbed)"
    }, 
    {
    "regex": "http://\\S*.collegehumor.com/video:\\S*", 
    "endpoint": "http://oohembed.com/oohembed/", 
    "name": "CollegeHumor Video (OohEmbed)"
    }, 
    {
    "regex": "http://\\S*.funnyordie.com/videos/\\S*", 
    "endpoint": "http://oohembed.com/oohembed/", 
    "name": "Funny or Die Video (OohEmbed)"
    }, 
    {
    "regex": "http://video.google.com/videoplay?\\S*", 
    "endpoint": "http://oohembed.com/oohembed/", 
    "name": "Google Video (OohEmbed)"
    }, 
    {
    "regex": "http://www.hulu.com/watch/\\S*", 
    "endpoint": "http://oohembed.com/oohembed/", 
    "name": "Hulu (OohEmbed)"
    }, 
    {
    "regex": "http://\\S*.metacafe.com/watch/\\S*", 
    "endpoint": "http://oohembed.com/oohembed/", 
    "name": "Metacafe (OohEmbed)"
    }, 
    {
    "regex": "http://(?:www\\.)?twitter\\.com/(?:\\w{1,20})/statuses/\\d+/?", 
    "endpoint": "http://oohembed.com/oohembed/", 
    "name": "Twitter Status (OohEmbed)"
    }, 
    {
    "regex": "http://\\S*.wikipedia.org/wiki/\\S*", 
    "endpoint": "http://oohembed.com/oohembed/", 
    "name": "Wikipedia (OohEmbed)"
    }, 
    {
    "regex": "http://(?:www\\.)?youtube\\.com/watch\\?v=[A-Za-z0-9\\-=_]{11}", 
    "endpoint": "http://www.youtube.com/oembed",
    "name": "YouTube"
    }, 
    {
    "regex": "http://(?:www\\.)?vimeo\\.com/\\d+", 
    "endpoint": "http://vimeo.com/api/oembed.json", 
    "name": "Vimeo"
    }, 
    {
    "regex": "http://(?:www\\.)?scribd\\.com/.*", 
    "endpoint": "http://www.scribd.com/services/oembed", 
    "name": "Scribd"
    },
    {
    "regex": "http://(?:www\\.)?blip\\.tv/.*",
    "endpoint": "http://blip.tv/oembed/",
    "name": "Blip.tv"
    },
    {
    "regex": "http://.*",
    "endpoint": "http://oohembed.com/oohembed/", 
    "name": "Catchall (OohEmbed)"
    },
]

_consumer = oembed.OEmbedConsumer()

for d in config:
    _consumer.addEndpoint(oembed.OEmbedEndpoint(d['endpoint'],
                                                ['regex:%s' % d['regex']]))

def oembed_expand(url, **opts):
    try:
        return _consumer.embed(url, **opts).getData()
    except (oembed.OEmbedError, urllib2.HTTPError):
        return None
