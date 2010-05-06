import cStringIO
import logging
import sys

try:
    import geopy
except ImportError:
    logging.warn('no geocoding support available')
    geopy = None

from django.conf import settings

def get_latitude_and_longitude(location):
    if geopy is None:
        raise ImportError("No module named geopy")
    google_key = getattr(settings, 'GOOGLE_API_KEY', None)
    if google_key:
        g = geopy.geocoders.Google(settings.GOOGLE_API_KEY)
    else:
        g = geopy.geocoders.GeoNames(output_format='json')
    oldstdout = sys.stdout
    try:
        sys.stdout = cStringIO.StringIO()
        try:
            some = list(g.geocode(location, exactly_one=False))
            if some:
                place, (lat, long) = some[0]
            else:
                lat = long = None
        except (ValueError, GQueryError) as ex:
            logging.exception("error in geocoding: %s" % str(ex))
            lat = long = None
    finally:
        sys.stdout = oldstdout
    return lat, long
