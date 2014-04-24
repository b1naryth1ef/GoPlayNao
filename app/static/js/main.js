

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

    ban_row: _.template('<tr class="ban-row"><td><%= ban.id %></td>'+
        '<td><a href="<%= url %>"><%= ban.user.username %></a></td>'+
        '<td><%= ban.reason %></td><td><%= ban.duration %></td></tr>'),

    forum_sidebar_header: _.template('<li class="list-group-item list-group-header"><%= cat.title %></li>'),
    forum_sidebar_item: _.template('<a href="#" class="list-group-item"><%= item.title %></a>')
    forum_thread: _.template('<div class="panel panel-default"><div class="panel-collapse collapse in">'+
        '<div class="panel-body">'+
        '<h3 style="margin-top: 0px; margin-bottom: 0px"><%= thread.title %></h3>'+
        '<b>Posted <%= thread.time %> ago by <a href="/u/0"><%= thread.author %></a></b>'+
        '</div></div></div>')

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
    matchid: null,
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
        // We fade these in because when we get here because if the JS
        //  has issues it will show mangled half-views of derpage.
        $("#lobby-maker").show();
        $("#lobby").show();

        pug.vglobal();
        if (id) {
            pug.lobbyJoin(id);
        } else {
            $("#lobby").hide();
            $("#btn-create-lobby").click(pug.lobbyCreate);
        }
    },

    lobbyHandleMsg: function (data) {
        // Just in case
        if (data.lobby != pug.lobbyid) {return;}

        switch(data.type) {
            case "chat":
                pug.lobbyAddChat(data.from, data.msg)
                break;
            case "join":
                pug.lobbyAddMember(data.member);
                pug.lobbyAddAction(data.msg, "success");
                break;
            case "quit":
                pug.lobbyRmvMember(data.member);
                pug.lobbyAddAction(data.msg, "danger");
                break;
            case "kick":
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
                $("#lobby-info-main-queued").hide();
                $("#lobby-accept-timer").countdown(function (){}, 10, "s");
                break;
            case "endmatch":
                $("#lobby-info-main-accepting").hide();
                $("#lobby-info-main-queued").show();
                break;
            case "accept":
                new Audio(SOUNDS.accept).play()
                $("#lobby-accept-info").show();
                $("#lobby-accept-accepted").text(data.num);
                $("#lobby-accept-size").text(data.size);
                if (data.num == data.size) {
                    // Set matchid
                    pug.matchid = data.id
                    // Delayed so its more fancy
                    setTimeout(pug.lobbyShowMatchInfo, 1500);
                    pug.lobbyAddAction("Match Found, number "+data.id+"!", "success");
                    $("#lobby-info-main-accepting").fadeOut();
                }
                break;
            case "delete":
                alert("This lobby has been closed!");
                window.location = "/";
                break;
            default:
                // sooooo not cool brah
                console.log("WTF:")
                console.log(data)
                break;
        }
    },

    // Displays a modal with match information/server ip
    lobbyShowMatchInfo: function () {
        $.ajax("/api/match/info", {
            data: {
                "id": pug.matchid
            },
            success: function(data) {
                if (data.success) {
                    $("#match-found-ip").text(data.match.server.ip)
                    $("#match-found-modal").modal('show')
                } else {
                    alert(data.msg);
                }
            }
        })
        
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
        $.ajax("/api/maps/list", {
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

        $("#lobby-accept-btn").click(function () {
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
                    $("#lobby-accept-btn").hide();
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
    },

    lobbyHandleState: function(state) {
        switch (state) {
            case LobbyState.LOBBY_STATE_IDLE:
            case LobbyState.LOBBY_STATE_CREATE:
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

    // Handles rendering the list of bans, and related pagination
    bansRender: function () {
        // Enable or disable back button based on page #
        if (pug.bans_page_num == 1) {
            $("#bans-page-prev").parent().addClass("disabled");
        } else {
            $("#bans-page-prev").parent().removeClass("disabled");
        }

        // Ajax call to the bans api
        $.ajax("/api/bans/list", {
            data: {
                page: pug.bans_page_num
            },
            success: function(data) {
                // Remove old pagination
                $(".bans-page").remove();

                // Enable or disable forward button based on page number
                if ((data.total < 100) || (pug.bans_page_num == data.total / 100)) {
                    $("#bans-page-next").parent().addClass("disabled");
                } else {
                    $("#bans-page-next").parent().removeClass("disabled");
                }

                // Render pagination
                _.each(_.range(1, (data.total / 100)+1), function(i) {
                    var active = (i == pug.bans_page_num) ? "active" : ""
                    $("#bans-page-before").before(
                        '<li class="'+active+'"><a id="'+i
                        +'" class="bans-page" href="">'+i+'</a></li>')
                });

                // Remove old ban rows
                $(".ban-row").remove();

                // Render ban rows
                _.each(data.bans, function (ban) {
                    $(".bans-list").append(JST.ban_row({ban: ban, url:"/u/"+ban.user.id}))
                })
            }
        })
    },

    // Called once on page load, handles binding events and loading the inital
    //  bans list.
    bans: function() {        
        $("#ban-pagination").delegate(".bans-page", "click", function (e) {
            e.preventDefault();
            e.stopPropagation();
            if (pug.bans_page_num == $(this).attr("id")) { return; }
            pug.bans_page_num = $(this).attr("id");
            pug.bansRender();
        })

        $("#bans-page-prev").click(function (e) {
            e.preventDefault();
            // If we're disabled, don't do shit
            if ($(this).parent().hasClass("disabled")) { return; }
            pug.bans_page_num--
            pug.bansRender();
        })

        $("#bans-page-next").click(function (e) {
            e.preventDefault();
            // If we're disabled, don't do shit
            if ($(this).parent().hasClass("disabled")) { return; }
            pug.bans_page_num++
            pug.bansRender();
        })

        pug.bansRender();
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

        $("#add-friend").click(function (e) {
            $.ajax("/api/users/friend", {
                data: {
                    id: u.id
                },
                success: function (data) {
                    if (data.success) {
                        alert("Friend request sent!")
                    } else {
                        alert("Error adding friend: "+data.msg)
                    }
                }
            })
        })
    },

    forums: function(fid, tid) {
        pug.forum_data = {
            forum: fid,
            thread: tid,
            page: 1,
        }

        if (pug.forum_data.thread) {
            pug.forum_load_thread()
        } else if (pug.forum_data.forum) {

        }

        pug.forum_load_sidebar()

        // TODO: click sidebar
    },

    forum_load_single: function () {
        $("/api/forum/threads/list", {
            data: {
                id: pug.forum_data.forum,
                page: pug.forum_data.forum
            },
            success: function (data) {

            }
        })
    },

    forum_load_thread: function() {
        $("/api/forum/threads/get", {
            data: {
                id: pug.forum_data.thread,
                page: pug.forum_data.page
            },
            success: function (data) {

            }
        })
    },

    forum_load_sidebar: function() {
        $.ajax("/api/forum/list", {
            success: function (data) {
                _.each(data.forums, function (forum) {
                    $("#forum-sidebar").append(
                        JST.forum_sidebar_header({
                            cat: forum
                        })
                    )

                    _.each(forum.children, function (child) {
                        $("#forum-sidebar").append(
                            JST.forum_sidebar_item({
                                item: child
                            })
                        )
                    })
                })
            }
        })
    }
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