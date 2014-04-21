from flask import Blueprint, render_template, g
from database import *
from util import *

public = Blueprint('public', __name__)

@public.route("/")
def public_index():
    return render_template("index.html")

@public.route("/lobby/<int:id>")
@public.route("/lobby")
@authed()
def public_lobby(id=None):
    if id:
        try:
            lobby = Lobby.get(Lobby.id == id)
        except Lobby.DoesNotExist:
            return flashy("That lobby does not exist!")
        if not lobby.canJoin(g.user):
            return flashy("You cannt join that lobby!")
        if lobby.state == LobbyState.LOBBY_STATE_UNUSED:
            return flashy("That lobby has expired!")

        # LOL SILLY, you can't be in more than one lobby at a time! Duh!
        for lob in Lobby.select().where((Lobby.members.contains(g.user.id)) & (Lobby.id != id)):
            lob.userLeave(g.user)

        lobby.joinLobby(g.user)
    return render_template("lobby.html", lobby=id)

@public.route("/friends")
@authed()
def public_friends():
    requests = list(g.user.getFriendRequests())
    friends = Friendship.select().where(((Friendship.usera == g.user) |
        (Friendship.userb == g.user)) &
        Friendship.active == True)
    friends = [i for i in friends]

    return render_template("friends.html",  friends=friends, requests=requests)

@public.route("/u/<user>")
def public_user(user=None):
    try:
        base_q = (User.username ** user)
        if user.isdigit():
            base_q |= (User.id == user)
        u = User.get(base_q)
    except User.DoesNotExist:
        return flashy("No such user!")

    return render_template("profile.html", user=u)

@public.route("/bans")
def public_bans():
    return render_template("bans.html")

@public.route("/about")
def public_about():
    return render_template("about.html")

@public.route("/matches")
def public_matches(): pass

@public.route("/match/<int:id>")
def public_match(id):
    try:
        match = Match.get(Match.id == id)
    except Match.DoesNotExist:
        return flashy("That match does not exist!")

    if match.level > g.user.level:
        return flashy("You do not have permission to view that!")

    return render_template("match.html", match=id)
