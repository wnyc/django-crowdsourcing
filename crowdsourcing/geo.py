import cStringIO
import logging
import sys

from geopy import geocoders

from django.conf import settings

def get_latitude_and_longitude(location):
    google_key=getattr(settings, 'GOOGLE_API_KEY', None)
    if google_key:
        g=geocoders.Google(settings.GOOGLE_API_KEY)
    else:
        g=geocoders.GeoNames(output_format='json')
    oldstdout=sys.stdout
    try:
        sys.stdout=cStringIO.StringIO()
        try:
            some=list(g.geocode(location, exactly_one=False))
            if some:
                place, (lat, long)=some[0]
            else:
                lat=long=None
        except ValueError:
            logging.exception("error in geocoding")
            lat=long=None
    finally:
        sys.stdout=oldstdout
    return lat, long

