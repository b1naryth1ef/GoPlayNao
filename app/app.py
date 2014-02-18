from flask import Flask, g, session, request
from views.public import public
from views.api import api
from database import User

app = Flask(__name__)
app.secret_key = "change_me"

app.register_blueprint(public)
app.register_blueprint(api)

@app.before_request
def beforeRequest():
    if request.cookies.get("sid"):
        s = Session.find(request.cookies.get("sid"))
        if not s:
            del request.cookies['sid']
        g.user = User.select().where(User.id == s['user']).get(0)

if __name__ == "__main__":
    app.run(debug=True)