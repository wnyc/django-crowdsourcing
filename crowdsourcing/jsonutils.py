from datetime import datetime, date, time

try:
    import simplejson as json
except ImportError:
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


class Encoder(json.JSONEncoder):
    def default(self, obj):
        if hasattr(obj, 'to_jsondata'):
            return obj.to_jsondata()
        for k in FORMATS:
            if isinstance(obj, k):
                return obj.strftime(FORMATS[k])
        return super(Encoder, self).default(obj)
