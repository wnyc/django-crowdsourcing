from datetime import datetime, date, time

import json


FORMATS = {datetime: "%Y-%m-%dT%H:%M:%S",
           date: '%Y-%m-%d',
           time: '%H:%M:%S'}


def dump(obj, fp, **kw):
    kw.setdefault('cls', Encoder)
    return json.dump(obj, fp, **kw)


def dumps(obj, **kw):
    kw.setdefault('cls', Encoder)
    return json.dumps(obj, **kw)


def datetime_to_string(dt):
    for k in FORMATS:
        if isinstance(dt, k):
            return dt.strftime(FORMATS[k])

class Encoder(json.JSONEncoder):
    def default(self, obj):
        if hasattr(obj, 'to_jsondata'):
            return obj.to_jsondata()
        dt_format = datetime_to_string(obj)
        return dt_format if dt_format else super(Encoder, self).default(obj)
