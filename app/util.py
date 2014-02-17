from twisted.web import resource
import ujson as json
from database import *

class AnyResource(resource.Resource):
    def render_GET(self, request): return self.render(request)
    def render_POST(self, request): return self.render(request)

class JsonResponse(AnyResource):
    """
    Represents a json resource, which is based on data given in a dictionary
    or list format. This returns the correct content encoding and meta
    tags for a json resource.
    """
    isLeaf = True

    def __init__(self, data):
        self.data = data
        resource.Resource.__init__(self)

    def render(self, request):
        request.setHeader("content-type", "application/json")
        return json.dumps(self.data)

class APIException(AnyResource):
    id = 0
    code = 500

    def __init__(self, msg, code=None):
        self.msg = msg
        self.code = code or self.code
        resource.Resource.__init__(self)

    def render(self, request):
        request.setHeader("content-type", "application/json")
        request.setResponseCode(self.code)
        return json.dumps({
            "id": self.id,
            "error": "%s: %s" % (self.__class__.__name__, self.msg)
        })

class InvalidMethod(APIException):
    id = 1
    code = 405

class APIError(APIException):
    id = 2
    code = 400

def allow(*methods):
    def deco(a):
        def _f(request, *args, **kwargs):
            if request.method not in methods:
                return InvalidMethodException("%s" % request.method)
            return a(request, *args, **kwargs)
        return _f
    return deco

def params(**required):
    def deco(b):
        def _f(request, *args, **kwargs):
            gathered = {}
            for k, v in required.items():
                if k not in request.args:
                    return APIError("Requires paramater `%s`" % k)
                val = request.args[k][0]
                try:
                    v(val)
                except:
                    return APIError("Paramater `%s` must be type `%s`" % (k, v))
                gathered[k] = val
            return b(request, **gathered)
        return _f
    return deco

def authed():
    def deco(c):
        def _f(request, **kwargs):
            id = request.getCookie("session")
            userid = get_session(id)
            if not userid:
                return APIError("No valid session!", 401)
            request.user = User.get(userid)
            if not request.user:
                return APIError("Invalid User!", 401)
            return c(request, **kwargs)
        return _f
    return deco
