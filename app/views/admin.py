from flask import Blueprint, render_template, g
from database import *
from util import *

admin = Blueprint('admin', __name__, url_prefix='/admin')

@admin.before_request
def before_admin_request():
    if not g.user or not g.user.level >= UserLevel.USER_LEVEL_MOD:
        return flashy("You are not authorized to view that!")

@admin.route("/")
def admin_index():
    return render_template("admin/index.html")
