from datetime import datetime, date, time
from google.appengine.ext import ndb
from flask.json import jsonify as fjsonify

from ndbextensions.models import Product, BtwType
from ndbextensions.utility import get_or_none


def recurse_encode(o):
    if isinstance(o, ndb.Model):
        a = recurse_encode(o.to_dict())
        a['id'] = o.key.urlsafe()
        return a
    elif isinstance(o, dict):
        return {k: recurse_encode(v) for k, v in o.iteritems()}
    elif isinstance(o, list):
        return [recurse_encode(v) for v in o]
    elif isinstance(o, ndb.Key):
        return o.urlsafe()
    elif isinstance(o, (datetime, date, time)):
        return str(o)
    else:
        return o


tofilter = ["group", "hidden", "value", "description", "amount", "budget", "email"]


def recurse_encode_filtered(o):
    if isinstance(o, ndb.Model):
        a = recurse_encode_filtered(o.to_dict())
        a['id'] = o.key.urlsafe()
        return a
    elif isinstance(o, dict):
        ret = {}
        for k, v in o.iteritems():
            if k in tofilter:
                continue
            ret[k] = recurse_encode_filtered(v)
        return ret
    elif isinstance(o, list):
        return [recurse_encode_filtered(v) for v in o]
    elif isinstance(o, ndb.Key):
        return o.urlsafe()
    elif isinstance(o, (datetime, date, time)):
        return str(o)
    else:
        return o


def jsonify(object, status_code=200):
    resp = fjsonify(recurse_encode(object))
    resp.status_code = status_code
    return resp


def transaction_recode(o):
    t = recurse_encode(o)

    for row in t['one_to_two']:
        row['contenttype'] = get_or_none(row["product"], Product).contenttype
        row['id'] = row['product']
        del row['value']
        del row['product']

    for i, row in enumerate(t['two_to_one']):
        row['contenttype'] = get_or_none(row["product"], Product).contenttype
        row['id'] = row['product']
        row['price'] = row['prevalue']
        del row['value']
        del row['product']

    for row in t['services']:
        row['contenttype'] = row['service']
        row['price'] = row['value']
        row['btw'] = get_or_none(row['btwtype'], BtwType).percentage
        del row['value']
        del row['service']
        del row['btwtype']

    return t
