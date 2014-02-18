from flask import request, flash, redirect, g
from database import Session, redis
from functools import wraps

def flashy(m, f="error", u="/"):
    flash(m, f)
    return redirect(u)

class DummyObj(object):
    def __init__(self, kwargs):
        self.__dict__.update(kwargs)

    def __getattr__(self, name):
        return None

def require(**need):
    result, missing = {}, False
    for k, v in need.items():
        if k not in request.values:
            missing = True
            continue
        try:
            result[k] = v(request.values.get(k))
        except:
            missing = True
    return DummyObj(result), not missing

def authed(level=0, err=None):
    def deco(f):
        @wraps(f)
        def _f(*args, **kwargs):
            if not g.user:
                return err() if err else "Error!", 400
            return f(*args, **kwargs)
        return _f
    return deco


def limit(per_minute):
    def deco(f):
        @wraps(f)
        def _f(*args, **kwargs):
            if 'server' not in g:
                k = "rl:%s" % request.remote_addr
                if not redis.exists(k):
                    redis.setex(k, 1, 60)
                    return f(*args, **kwargs)
                if int(redis.get(k)) > per_minute:
                    return "Too many requests per minute!", 429
                redis.incr(k)
            return f(*args, **kwargs)
        return _f
    return deco
