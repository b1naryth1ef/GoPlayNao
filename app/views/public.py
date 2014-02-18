from flask import Blueprint, render_template, flash, redirect, request, g, session
from database import User, Session
from util import *
import time

public = Blueprint('public', __name__)

@public.route("/login")
def public_login():
    args, success = require(username=str, password=str)
    if not success:
        return flashy("Invalid Login Request!")

    try:
        u = User.select().where(User.username == args.username | User.email == args.email).get()
        if not u.checkPassword(args.password):
            raise Exception()
        if not u.isValid():
            return flashy("Inactive user account!")
    except User.DoesNotExist:
        return flashy("Incorrect username or password!")

    sid = u.login()
    resp = flashy("Welcome back %s!" % u.username, "success")
    resp.set_cookie("sid", sid, expires=time.time() + Session.LIFETIME)

    return resp

# TODO: moveme
@public.route("/logout")
def public_logout():
    pass