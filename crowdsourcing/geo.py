import cStringIO
import logging
import sys

try:
    import geopy
except ImportError:
    logging.warn('no geocoding support available')
    geopy = None

from django.conf import settings

from . import settings as local_settings

def get_latitude_and_longitude(location):
    if geopy is None:
        raise ImportError("No module named geopy")
    g = geopy.geocoders.Google()
    oldstdout = sys.stdout
    try:
        sys.stdout = cStringIO.StringIO()
        try:
            some = list(g.geocode(location, exactly_one=False))
            if some:
                place, (lat, long) = some[0]
            else:
                lat = long = None
        except Exception as ex:
            logging.exception("error in geocoding: %s" % str(ex))
            lat = long = None
    finally:
        sys.stdout = oldstdout
    return lat, long
