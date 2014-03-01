

var LobbyState = {
    LOBBY_STATE_CREATE: 1,
    LOBBY_STATE_IDLE: 2,
    LOBBY_STATE_SEARCH: 3,
    LOBBY_STATE_PLAY: 4,
    LOBBY_STATE_UNUSED: 5
}


var JST = {
    invite: _.template('<li id="side-bar-invite"><div class="col-left">'+
            '<span class="label label-info"><i class="icon-envelope"></i></span></div>'+
            '<div class="col-right with-margin">'+
            '<a href="<%= url %>"><span class="message"><%= msg %></span></a></li>'),

    lobbyFriend: _.template('<tr id="friend-<%= f.id %>"><td><%= f.username %></td>'+
        '<td><a href="" id="<%= f.id %>" class="label label-primary lobby-invite">Invite</a></td></tr>'),

    lobbyMember: _.template('<tr id="member-<%= m.id %>"><td><%= m.username %></td>'+
        '<% if (leader && m.id != us) { %><td id="<%= m.id %>"><a href="" id="lobby-kick-member" class="label label-danger lobby-kick">kick</a></td><% } %></tr>'),

    lobbyMap: _.template('<option <%= selected ? "selected" : ""%> style="height: 100px; width: 100px;"'+
        ' data-img-src="/api/maps/image?map=<%- id %>&height=200&width=300"'+
        ' value="<%= name %>"><%= title %></option>'),

    search_base: _.template('<li class="search-result"><a href="/u/<%= u.username %>"><div class="col-left">'+
                        '<span class="label label-info"><i class="icon-star"></i></span>'+
                        '</div><div class="col-right with-margin">'+
                        '<span class="message"><strong><%= u.username %></strong></span>'+
                        '<span class="time">32 Pugs Played</span></div></a> </li>'),

    ban_row: _.template('<tr><td><%= ban.id %></td>'+
        '<td><a href="<%= url %>"><%= ban.user.username %></a></td>'+
        '<td><%= ban.reason %></td><td><%= ban.duration %></td></tr>')

}

var SOUNDS = {
    invite: "/static/sound/notification.mp3",
    accept: "/static/sound/ding.mp3",
}

// YOLO BROLO :)
function buildState(statea, stateb) {
    var obj = {
        a: statea,
        b: stateb,
        c: 1,
        run: function (i) {
            obj.c = i;
            this.flip(false);
        },
        flip: function (change) {
            if (change == undefined) { change = true; }
            if (obj.c) {
                var a = obj.a, b = obj.b;
                if (change) obj.c = 0;
            } else {
                var a = obj.b, b = obj.a;
                if (change) obj.c = 1;
            }
            for (i in a) {
                $(a[i]).show()
            }
            for (i in b) {
                $(b[i]).hide()
            }
        }
    }
    obj.flip()
    return obj
}

var pug = {
    lobbyid: null,
    lobbypoll: 0,
    lobbydata: null,
    lobbymembers: [],
    config: {},
    pollLobbyInterval: null,
    getStatsInterval: null,
    bg: false,
    socket: null,

    // View: bans
    bans_page_num: 1,

    // -- HTML5 Wrappers --
    storeLocal: function(k, v) {
        if (!Modernizr.localstorage) {
            return false;
        }
        localStorage.setItem(k, v);
    },

    getLocal: function (k) {
        if (!Modernizr.localstorage) {
            return null;
        }
        return localStorage.getItem(k)
    },

    pushurl: function(url) {
        if (history) {
            history.pushState({}, '', url)
        }
    },

    notify: function(msg) {
        if (!window.webkitNotifications) { return; }
        if (window.webkitNotifications.checkPermission() == 0) {
            window.webkitNotifications.createNotification('icon.png', msg.title, msg.content);
        }
    },

    // TODO: use this in a click event
    notifyRequestPerms: function () {
        window.webkitNotifications.requestPermission()
    },

    // -- General Shit --
    msg: function(content, type, location, dismiss, cls) {
        var cls = cls ? cls : "";
        var dismiss = dismiss ? '<i class="icon-remove close" data-dismiss="alert"></i> ' : '';
        var alert = '<div style="text-align: center;" class="alert alert-'+type+' fade in '+cls+'">'+dismiss+content+'</div>';
        $(location).prepend(alert);
    },

    hidemsg: function(cls) {
        $("."+cls).remove();
    },

    vglobal: function() {
        var search = function() {
            $(".search-result").remove()
            $.ajax("/api/users/search", {
                type: "POST",
                data: {
                    query: $("#search-input").val()
                },
                success: function (data) {
                    $(".sidebar-search-results").slideDown(200);
                    if (data.success) {
                        for (eid in data.results) {
                            $("#search-results").append(JST.search_base({u: data.results[eid]}))
                        }
                    }
                }
            })
        }

        $('#search-submit').click(function(e) {
            e.preventDefault()
            search()
        })
        $('#search-input').keypress(function(e) {
            if(e.which == 13) {
                e.preventDefault();
                search()
            }
        });

        $(".sidebar-search-results .close").click(function () {
            $(".sidebar-search-results").slideUp(200)
        });

        // Start up some socket shit dawg
        var port = location.port ? ":"+location.port : ""
        pug.socket = io.connect('http://' + document.domain + port + "/api/poll");
        pug.socket.on('lobby', pug.lobbyHandleMsg);
        pug.socket.on('global', pug.handleGlobal);

        // This interval makes sure we stay active in lobbies/etc
        setInterval(function () {
            pug.socket.emit("ping", {lobby: pug.lobbyid})
        }, 1000 * 5)
    },

    handleGlobal: function (msg) {
        switch (msg.type) {
            case "stats":
                pug.handleStats(msg.data);
                break;
            case "invite":
                pug.handleInvite(msg.data);
                break;
        }
    },

    handleInvite: function (data) {
        var sbn = $("#side-bar-notifications");
        sbn.append(JST.invite(data))

        flashTitle("New Invitation!");

        // Play Invite Sounds
        new Audio(SOUNDS.invite).play()

        if (sbn.children().length > 4) {
            var obj = sbn.children()[4];
            $(obj).fadeOut().remove();
        }
    },

    lobby: function (id) {
        pug.vglobal();
        if (id) {
            pug.lobbyJoin(id);
        } else {
            $("#lobby").hide();
            $("#btn-create-lobby").click(pug.lobbyCreate);
        }
    },

    lobbyHandleMsg: function (data) {
        switch(data.type) {
            case "chat":
                pug.lobbyAddChat(data.from, data.msg)
                break;
            case "join":
                pug.lobbyAddMember(data.member);
                pug.lobbyAddAction(data.msg, "success");
                break;
            case "quit":
                if (data.member == USER.id) {
                    alert("You've been kicked from the lobby!");
                    window.location = "/"
                }
                pug.lobbyRmvMember(data.member);
                pug.lobbyAddAction(data.msg, "danger");
                break;
            case "state":
                pug.lobbyHandleState(data.state);
                pug.lobbyAddAction(data.msg, "warning");
                break;
            case "msg":
                pug.lobbyAddAction(data.msg, data.cls || "danger");
                break;
            case "match":
                $("#lobby-info-main-accepting").show();
                break;
            case "accept":
                $("#lobby-accepted").text(data.num);
                if (data.num == 10) {
                    // Delayed so we can show fancy animations for accepted!
                    setTimeout(function () {
                        window.location = "/match/"+data.id;
                    }, 3000);
                    pug.lobbyAddAction("Match Found, number "+data.id+"!", "success");
                    $("#lobby-info-main-accepting").fadeOut();
                    new Audio(SOUNDS.accept).play()
                }
                break;
            default:
                // sooooo not cool brah
                console.log("WTF:")
                console.log(data)
                break;
        }
    },

    lobbyCreate: function(e) {
        // This should never happen unless people are firing manual events
        if (pug.lobbyid) {
            alert("Something went wrong! (Refresh the page?)");
            return
        }

        // Fade out the lobby creation wizard, and add in the loader
        $("#lobby-create-wizard").hide();
        $("#lobby-create-loader").fadeIn();

        // Function that handles error state
        var error = function (data) {
            var msg = data.msg ? data.msg : "Something went wrong!"
            // We hide the loader and reshow the wizard, in case its a user-correctabble
            //  error.
            $("#lobby-create-loader").hide();
            $("#lobby-create-wizard").show();
            pug.msg(msg, "danger", "#lobby-maker-main", false, "lobby-maker-err");
        }

        // Hide old errors
        pug.hidemsg("lobby-maker-err");

        // Make the request to create a lobby, pug.config is empty for now
        //  in the future it should contain base settings ??? or be removed ???
        $.ajax("/api/lobby/create", {
            type: "POST",
            data: {
                config: JSON.stringify(pug.config)
            },
            success: function(data) {
                // Well dix, looks like we failed...
                if (!data.success) {
                    error(data);
                }
                // Hide loader
                $("#lobby-create-loader").hide();
                // Save lobby id, render
                pug.lobbyid = data.id;

                pug.pushurl(window.location+"/"+data.id)
                pug.lobbydata = data;
                pug.lobbyRender();
            },
            error: error
        })
    },

    lobbyJoin: function(id) {
        if (!pug.lobbyid) {
            pug.lobbyid = id;
        }

        $.ajax("/api/lobby/info", {
            data: {
                id: pug.lobbyid
            },
            success: function (data) {
                if  (data.success) {
                    pug.lobbydata = data.lobby
                    pug.lobbyRender()
                } else {
                    alert(data.msg)
                }
            }
        });
        
    },
    lobbyAddMember: function(m) {
        var isLeader = (USER.id == pug.lobbydata.owner)
        if ($.inArray(m.id, pug.lobbymembers) != -1) {
            return;
        }
        $("#lobby-member-list").append(JST.lobbyMember({m: m, leader: isLeader, us: USER.id}));
        pug.lobbymembers.push(m.id)
    },

    lobbyRmvMember: function(id) {
        $("#member-"+id).remove();
    },

    lobbyRenderFriends: function() {
        $.ajax("/api/users/friends", {
            success: function (data) {
                if (data.success) {
                    $.each(data.friends.online, function(_, v) {
                        if ($.inArray(v.id, pug.lobbymembers) != -1) {
                            return;
                        }
                        $("#lobby-friends-list").append(JST.lobbyFriend({f: v}))
                    });
                }
            }
        })
    },

    lobbyRenderMapSelection: function() {
        $.ajax("/api/maps", {
            success: function (data) {
                base = pug.getLocal("maps");
                _.each(data, function (v) {
                    // If we have some local stored data, set map selection
                    //  based on that. Otherwise just set every map as selected
                    if (base) {
                        // If we exist, we're selected otherwise gtfo
                        if (base.indexOf(v.name) > -1) {
                            v.selected = true;
                        } else {
                            v.selected = false;
                        }
                    } else {
                        v.selected = true;
                    }
                    $("#lobby-map-list").append(JST.lobbyMap(v))
                })

                $("#lobby-map-list").imagepicker({
                    show_label: true,
                    changed: function (oldv, newv) {
                        pug.config.maps = newv;
                        pug.storeLocal("maps", newv)
                    }
                })
            }
        })

    },

    lobbyRender: function() {
        $("#lobby-maker").hide();
        $("#lobby").show();
        $("#lobby-chat-list").slimScroll({
            height: '350px',
            start: 'bottom',
        });

        if (pug.lobbydata.owner != USER.id) {
            $(".not-owner").show()
        } else {
            $(".owner").show()
            pug.lobbyRenderMapSelection();
        }

        // Eventaully we should turn this into a websocket thing
        setInterval(pug.lobbyRenderFriends(), 1000 * 10);

        $.each(pug.lobbydata.members, function(_, v) {
            pug.lobbyAddMember(v)
        })

        if (pug.lobbydata.owner == USER.id) {
            var lobbySettingsState = buildState(["#lobby-queue-start", "#lobby-settings-edit"], ["#lobby-info-main-selection", "#lobby-settings-save"]);

            $("#lobby-settings-save").click(function () {
                $.ajax("/api/lobby/edit", {
                    type: "POST",
                    data: {
                        id: pug.lobbyid,
                        config: JSON.stringify(pug.config)
                    },
                    success: function(data) {
                        if (!data.success) {
                            alert(data.msg);
                        }
                    },
                })

                lobbySettingsState.run(1);
            })

            $("#lobby-settings-edit").click(function () {
                lobbySettingsState.run(0);
            })
        }

        $("#lobby-accept").click(function () {
            $.ajax("/api/lobby/action", {
                type: "POST",
                data: {
                    id: pug.lobbyid,
                    action: "accept",
                },
                success: function(data) {
                    if (!data.success) {
                        alert(data.msg)
                    }
                }
            })
        })

        $("#lobby-friends").delegate(".lobby-invite", "click", function (e) {
            e.preventDefault();
            e.stopPropagation();
            $.ajax("/api/lobby/invite", {
                type: "POST",
                data: {
                    lid: pug.lobbyid,
                    uid: $(this).attr("id")
                }
            });
        });

        $("#lobby-list").delegate("#lobby-kick-member", "click", function (e) {
            e.preventDefault();
            e.stopPropagation();
            $.ajax("/api/lobby/action", {
                type: "POST",
                data: {
                    id: pug.lobbyid,
                    action: "kick",
                    user: $(this).parent().attr("id")
                },
                success: function(data) {
                    if (!data.success) {
                        alert(data.msg)
                    }
                }
            })
        });

        $("#lobby-queue-start").click(function () {
            $.ajax("/api/lobby/action", {
                type: "POST",
                data: {
                    id: pug.lobbyid,
                    action: "start"
                },
                success: pug.lobbyPollStart
            })
        });
        $("#lobby-queue-stop").click(function () {
            $.ajax("/api/lobby/action", {
                type: "POST",
                data: {
                    id: pug.lobbyid,
                    action: "stop"
                },
                success: pug.lobbyPollStart
            })
        });

        $("#lobby-leave").click(function () {
            $.ajax("/api/lobby/action", {
                type: "POST",
                data: {
                    id: pug.lobbyid,
                    action: "leave"
                },
                success: function (data) {
                    if (data.success) {
                        window.location = '/'
                    }
                }
            })
        })

        // The following handles sending chat messages
        var send_lobby_chat = function () {
            var msg = $("#lobby-chat-text").val();
            $.ajax("/api/lobby/chat", {
                type: "POST",
                data: {
                    id: pug.lobbyid,
                    msg: msg
                },
                success: function(data) {
                    if (data.success) {
                        $("#lobby-chat-text").val("");
                    }
                }
            })
        }
        // Bind send button
        $("#lobby-chat-send").click(send_lobby_chat)
        // Bind the enter key
        $('#lobby-chat-text').keypress(function(e) {
            if(e.which == 13) {
                send_lobby_chat();
            }
        });
        pug.lobbyHandleState(pug.lobbydata.state)

        $("#lobby-invite-btn").click(function () {
            $("#invite-modal").modal('show')
        })
    },

    lobbyHandleState: function(state) {
        switch (state) {
            case LobbyState.LOBBY_STATE_CREATE:
            case LobbyState.LOBBY_STATE_IDLE:
            case LobbyState.LOBBY_STATE_UNUSED:
                $("#lobby-info-main-queued").hide();
                $("#lobby-info-main-waiting").show();
                break;
            case LobbyState.LOBBY_STATE_SEARCH:
                $("#lobby-info-main-queued").show();
                $("#lobby-info-main-waiting").hide();
                break;
        }
    },

    lobbyAddChat: function(from, msg) {
        $("#lobby-chat-list").append('<li class="list-group-item basic-alert"><b>'+from+':</b> '+msg+'</li>')
        $("#lobby-chat-list").animate({ scrollTop: $('#lobby-chat-list')[0].scrollHeight}, 700);
    },

    lobbyAddAction: function(text, color) {
        var extra = color ? ' class="text-'+color+'" ' : ''
        $("#lobby-chat-list").append('<li class="list-group-item basic-alert"><i'+extra+'>'+text+'</i></li>')
        $("#lobby-chat-list").animate({ scrollTop: $('#lobby-chat-list')[0].scrollHeight}, 700);
    },

    handleStats: function (data) {
        $(".apistats").each(function (_, i) {
            var id = $(i).attr("id").split(".")
            var base = data;
            for (get in id) {
                base = base[id[get]]
            }
            $(i).text(base)
        })
    },

    // Loads stats from the backend and dynamically loads them into values
    getStats: function () {
        $.ajax("/api/stats", {success: pug.handleStats})
    },

    friends: function() {
        pug.vglobal();
        $(".friends-unfriend").click(function (e) {
            $.ajax("/api/users/unfriend", {
                type: "POST",
                data: {
                    id: $(this).attr("id")
                },
                success: function (data) {
                    if (data.success) {
                        // FIXME
                        $($(this).parent()).remove()
                        pug.msg("Removed friend!", "success", "#friends-main", true)
                    }
                }
            });
        });

        $(".friends-deny").click(function (e) {
            var dis = $(this)
            $.ajax("/api/invites/deny", {
                type: "POST",
                data: {
                    id: $(this).attr("id")
                },
                success: function (data) {
                    if (data.success) {
                        dis.parents()[1].remove()
                        pug.msg("Denied Friend Invite!", "warning", "#friends-main", true)
                    }
                }
            })
        });

        $(".friends-accept").click(function (e) {
            var dis = $(this);
            $.ajax("/api/invites/accept", {
                type: "POST",
                data: {
                    id: $(this).attr("id")
                },
                success: function (data) {
                    if (data.success) {
                        dis.parents()[1].remove()
                        pug.msg("Accepted Friend Invite!", "success", "#friends-main", true)
                        setTimeout(location.refresh, 3000);
                    }
                }
            })
        });
    },

    // Bans view
    bans: function() {
        $.ajax("/api/bans/list", {
            data: {
                page: this.bans_page_num
            },
            success: function(data) {
                _.each(data.bans, function (ban) {
                    if (ban.steamid) {
                        url = "steamcommunity.com/profiles/"+ban.steamid
                    } else {
                        url = "/u/"+ban.user.id
                    }
                    $(".bans-list").html(JST.ban_row({ban: ban, url:url}))
                })
            }
        })
    },

    // Profile view
    profile: function(u) {
        $.ajax("/api/users/stats", {
            data: {
                id: u.id
            },
            success: function (data) {
                if (data.success) {
                    graph_drawPlayerOverview(data.stats, "#profile-graph-overview")
                }
            }
        })
    },
}

$(document).ready(function () {
    // We immediatly load stats to display on the page, websocket will keep
    //  this going
    pug.getStats();

    // Warn users that do not have good support for our features
    if (!Modernizr.websockets || !Modernizr.localstorage || !Modernizr.history || !window.webkitNotifications || !window.JSON) {
        $(".bad-browser-alert").fadeIn();
    }
});