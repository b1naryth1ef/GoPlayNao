var App = function () {
    var o = false;
    var n = false;
    var l = false;
    var b = [];
    var m = {
        blue: "#54728c",
        red: "#e25856",
        green: "#94B86E",
        purple: "#852b99",
        grey: "#555555",
        yellow: "#ffb848"
    };
    var w = "250px";
    var v = function () {
        var y = (navigator.userAgent.match(/msie [8]/i));
        var x = (navigator.userAgent.match(/msie [9]/i));
        var z = !! navigator.userAgent.match(/MSIE 10/);
        if (z) {
            $("html").addClass("ie10")
        }
        $(".navbar li.nav-toggle").click(function () {
            $("body").toggleClass("nav-open")
        });
        $(".toggle-sidebar").click(function (B) {
            B.preventDefault();
            $("#sidebar").css("width", "");
            $("#sidebar > #divider").css("margin-left", "");
            $("#content").css("margin-left", "");
            $("#container").toggleClass("sidebar-closed")
        });
        $(".toggle-top-left-menu").click(function (B) {
            B.preventDefault();
            $(".navbar-left.navbar-left-responsive").slideToggle(200)
        });
        var A = function () {
            $(".crumbs .crumb-buttons > li").removeClass("first");
            $(".crumbs .crumb-buttons > li:visible:first").addClass("first");
            if ($("body").hasClass("nav-open")) {
                $("body").toggleClass("nav-open")
            }
            $(".navbar-left.navbar-left-responsive").removeAttr("style");
            h();
            c()
        };
        $(window).setBreakpoints({
            breakpoints: [320, 480, 768, 979, 1200]
        });
        $(window).bind("exitBreakpoint320", function () {
            A()
        });
        $(window).bind("enterBreakpoint320", function () {
            A();
            s()
        });
        $(window).bind("exitBreakpoint480", function () {
            A()
        });
        $(window).bind("enterBreakpoint480", function () {
            A();
            s()
        });
        $(window).bind("exitBreakpoint768", function () {
            A()
        });
        $(window).bind("enterBreakpoint768", function () {
            A();
            s()
        });
        $(window).bind("exitBreakpoint979", function () {
            A()
        });
        $(window).bind("enterBreakpoint979", function () {
            A()
        });
        $(window).bind("exitBreakpoint1200", function () {
            A()
        });
        $(window).bind("enterBreakpoint1200", function () {
            A()
        })
    };
    var q = function () {
        $("body").height("100%");
        var A = $(".header");
        var C = A.outerHeight();
        var x = $(document).height();
        var z = $(window).height();
        var y = x - z;
        if (y <= C) {
            var B = x - y
        } else {
            var B = x
        }
        B = B - C;
        var x = $(document).height();
        $("body").height(B)
    };
    var t = function () {
        q();
        if ($(".header").hasClass("navbar-fixed-top")) {
            $("#container").addClass("fixed-header")
        }
    };
    var u = function () {
        var x = g(r, 30);
        $(window).resize(x)
    };
    var r = function () {
        q();
        if ($.fn.dataTable) {
            var x = $.fn.dataTable.fnTables(true);
            $(x).each(function () {
                if (typeof $(this).data("horizontalWidth") != "undefined") {
                    $(this).dataTable().fnAdjustColumnSizing()
                }
            })
        }
    };
    var g = function (B, E, y) {
        var D, z, A, C, x;
        return function () {
            A = this;
            z = arguments;
            C = new Date();
            var G = function () {
                var H = (new Date()) - C;
                if (H < E) {
                    D = setTimeout(G, E - H)
                } else {
                    D = null;
                    if (!y) {
                        x = B.apply(A, z)
                    }
                }
            };
            var F = y && !D;
            if (!D) {
                D = setTimeout(G, E)
            }
            if (F) {
                x = B.apply(A, z)
            }
            return x
        }
    };
    var f = function () {
        if ($(window).width() <= 767) {
            $("body").on("movestart", function (y) {
                if ((y.distX > y.distY && y.distX < -y.distY) || (y.distX < y.distY && y.distX > -y.distY)) {
                    y.preventDefault()
                }
                var x = $(y.target).parents("#project-switcher");
                if (x.length) {
                    y.preventDefault()
                }
            }).on("swipeleft", function (x) {
                $("body").toggleClass("nav-open")
            }).on("swiperight", function (x) {
                $("body").toggleClass("nav-open")
            })
        }
    };
    var d = function () {
        var z = "icon-angle-down",
            y = "icon-angle-left";
        $("li:has(ul)", "#sidebar-content ul").each(function () {
            if ($(this).hasClass("current") || $(this).hasClass("open-default")) {
                $(">a", this).append("<i class='arrow " + z + "'></i>")
            } else {
                $(">a", this).append("<i class='arrow " + y + "'></i>")
            }
        });
        if ($("#sidebar").hasClass("sidebar-fixed")) {
            $("#sidebar-content").append('<div class="fill-nav-space"></div>')
        }
        $("#sidebar-content ul > li > a").on("click", function (C) {
            if ($(this).next().hasClass("sub-menu") == false) {
                return
            }
            if ($(window).width() > 767) {
                var B = $(this).parent().parent();
                B.children("li.open").children("a").children("i.arrow").removeClass(z).addClass(y);
                B.children("li.open").children(".sub-menu").slideUp(200);
                B.children("li.open-default").children(".sub-menu").slideUp(200);
                B.children("li.open").removeClass("open").removeClass("open-default")
            }
            var A = $(this).next();
            if (A.is(":visible")) {
                $("i.arrow", $(this)).removeClass(z).addClass(y);
                $(this).parent().removeClass("open");
                A.slideUp(200, function () {
                    $(this).parent().removeClass("open-fixed").removeClass("open-default");
                    q()
                })
            } else {
                $("i.arrow", $(this)).removeClass(y).addClass(z);
                $(this).parent().addClass("open");
                A.slideDown(200, function () {
                    q()
                })
            }
            C.preventDefault()
        });
        var x = function () {
            $("#divider.resizeable").mousedown(function (B) {
                B.preventDefault();
                var A = $("#divider").width();
                $(document).mousemove(function (D) {
                    var C = D.pageX + A;
                    if (C <= 300 && C >= (A * 2 - 3)) {
                        if (C >= 240 && C <= 260) {
                            $("#sidebar").css("width", 250);
                            $("#sidebar-content").css("width", 250);
                            $("#content").css("margin-left", 250);
                            $("#divider").css("margin-left", 250)
                        } else {
                            $("#sidebar").css("width", C);
                            $("#sidebar-content").css("width", C);
                            $("#content").css("margin-left", C);
                            $("#divider").css("margin-left", C)
                        }
                    }
                })
            });
            $(document).mouseup(function (A) {
                $(document).unbind("mousemove")
            })
        };
        x()
    };
    var s = function () {
        $("#sidebar").css("width", "");
        $("#sidebar-content").css("width", "");
        $("#content").css("margin-left", "");
        $("#divider").css("margin-left", "")
    };
    var h = function () {
        var x = /android.*chrom(e|ium)/.test(navigator.userAgent.toLowerCase());
        if (/Android|webOS|iPhone|iPad|iPod|BlackBerry/i.test(navigator.userAgent) && x == false) {
            $("#sidebar").css("overflow-y", "auto")
        } else {
            if ($("#sidebar").hasClass("sidebar-fixed") || $(window).width() <= 767) {
                if (x && !$("#sidebar").hasClass("sidebar-fixed-responsive")) {
                    var y = 100;
                    $("#sidebar").attr("style", "position: absolute !important;");
                    if ($(window).width() > 979) {
                        $("#sidebar").css("margin-top", "-52px")
                    }
                    if ($(window).width() <= 767) {
                        $("#sidebar").css("margin-left", "-250px").css("margin-top", "-52px")
                    }
                } else {
                    var y = 7;
                    $("#sidebar-content").slimscroll({
                        height: "100%",
                        wheelStep: y
                    })
                }
            }
        }
    };
    var e = function () {
        function x(A) {
            $("body").removeClass(function (B, C) {
                return (C.match(/\btheme-\S+/g) || []).join(" ")
            });
            $("body").addClass("theme-" + A);
            $.cookie("theme", A, {
                path: "/"
            });
            if (A == "dark") {
                y("add")
            } else {
                y("remove")
            }
        }

        function y(A) {
            $("#theme-switcher .btn").each(function () {
                if (A == "add") {
                    $(this).addClass("btn-inverse")
                } else {
                    $(this).removeClass("btn-inverse")
                }
            })
        }
        if ($.cookie) {
            $("#theme-switcher label").click(function () {
                var A = $(this).find("input");
                var B = A.data("theme");
                x(B)
            });
            if ($.cookie("theme")) {
                var z = $.cookie("theme");
                x(z);
                $("#theme-switcher input").each(function () {
                    var A = $(this);
                    var B = A.data("theme");
                    if (B == z) {
                        A.parent().addClass("active")
                    } else {
                        A.parent().removeClass("active")
                    }
                });
                if (z == "dark") {
                    y("add")
                } else {
                    y("remove")
                }
            }
        }
    };
    var i = function () {
        $(".widget .toolbar .widget-collapse").click(function () {
            var A = $(this).parents(".widget");
            var x = A.children(".widget-content");
            var z = A.children(".widget-chart");
            var y = A.children(".divider");
            if (A.hasClass("widget-closed")) {
                $(this).children("i").removeClass("icon-angle-up").addClass("icon-angle-down");
                x.slideDown(200, function () {
                    A.removeClass("widget-closed")
                });
                z.slideDown(200);
                y.slideDown(200)
            } else {
                $(this).children("i").removeClass("icon-angle-down").addClass("icon-angle-up");
                x.slideUp(200, function () {
                    A.addClass("widget-closed")
                });
                z.slideUp(200);
                y.slideUp(200)
            }
        })
    };
    var k = function () {
        $(".table-checkable thead th.checkbox-column :checkbox").on("change", function () {
            var z = $(this).prop("checked");
            var x = $(this).parents("table.table-checkable").data("horizontalWidth");
            if (typeof x != "undefined") {
                var y = $(this).parents(".dataTables_scroll").find(".dataTables_scrollBody tbody")
            } else {
                var y = $(this).parents("table").children("tbody")
            }
            y.each(function (B, A) {
                $(A).find(".checkbox-column").each(function (D, C) {
                    var E = $(":checkbox", $(C)).prop("checked", z).trigger("change");
                    if (E.hasClass("uniform")) {
                        $.uniform.update(E)
                    }
                    $(C).closest("tr").toggleClass("checked", z)
                })
            })
        });
        $(".table-checkable tbody tr td.checkbox-column :checkbox").on("change", function () {
            var x = $(this).prop("checked");
            $(this).closest("tr").toggleClass("checked", x)
        });
        $(".datatable.table-checkable").bind("draw", function () {
            var y = $("tbody tr td.checkbox-column :checkbox", this).length;
            var A = $("tbody tr td.checkbox-column :checkbox:checked", this).length;
            var z = $("thead th.checkbox-column :checkbox", this);
            var x = false;
            if (y == A && y != 0) {
                x = true
            } else {
                x = false
            }
            z.prop("checked", x);
            if (z.hasClass("uniform")) {
                $.uniform.update(z)
            }
        })
    };
    var j = function () {
        var y = function (z) {
            $(z).each(function () {
                var B = $($($(this).attr("href")));
                var A = $(this).parent().parent();
                if (A.height() > B.height()) {
                    B.css("min-height", A.height())
                }
            })
        };
        $("body").on("click", '.nav.nav-tabs.tabs-left a[data-toggle="tab"], .nav.nav-tabs.tabs-right a[data-toggle="tab"]', function () {
            y($(this))
        });
        y('.nav.nav-tabs.tabs-left > li.active > a[data-toggle="tab"], .nav.nav-tabs.tabs-right > li.active > a[data-toggle="tab"]');
        if (location.hash) {
            var x = location.hash.substr(1);
            $('a[href="#' + x + '"]').click()
        }
    };
    var a = function () {
        $(".scroller").each(function () {
            $(this).slimScroll({
                size: "7px",
                opacity: "0.2",
                position: "right",
                height: $(this).attr("data-height"),
                alwaysVisible: ($(this).attr("data-always-visible") == "1" ? true : false),
                railVisible: ($(this).attr("data-rail-visible") == "1" ? true : false),
                disableFadeOut: true
            })
        })
    };
    var p = function () {
        c();
        $(".project-switcher-btn").click(function (z) {
            z.preventDefault();
            x(this);
            $(this).parent().toggleClass("open");
            var A = y(this);
            $(A).slideToggle(200, function () {
                $(this).toggleClass("open")
            })
        });
        $("body").click(function (A) {
            var z = A.target.className.split(" ");
            if ($.inArray("project-switcher", z) == -1 && $.inArray("project-switcher-btn", z) == -1 && $(A.target).parents().index($(".project-switcher")) == -1 && $(A.target).parents(".project-switcher-btn").length == 0) {
                x()
            }
        });
        $(".project-switcher #frame").each(function () {
            $(this).slimScrollHorizontal({
                width: "100%",
                alwaysVisible: true,
                color: "#fff",
                opacity: "0.2",
                size: "5px"
            })
        });
        var x = function (z) {
            $(".project-switcher").each(function () {
                var A = $(this);
                if (A.is(":visible")) {
                    var B = y(z);
                    if (B != ("#" + A.attr("id"))) {
                        $(this).slideUp(200, function () {
                            $(this).toggleClass("open");
                            $(".project-switcher-btn").each(function () {
                                var C = y(this);
                                if (C == ("#" + A.attr("id"))) {
                                    $(this).parent().removeClass("open")
                                }
                            })
                        })
                    }
                }
            })
        };
        var y = function (z) {
            var A = $(z).data("projectSwitcher");
            if (typeof A == "undefined") {
                A = "#project-switcher"
            }
            return A
        }
    };
    var c = function () {
        $(".project-switcher").each(function () {
            var y = $(this);
            y.css("position", "absolute").css("margin-top", "-1000px").show();
            var x = 0;
            $("ul li", this).each(function () {
                x += $(this).outerWidth(true) + 15
            });
            y.css("position", "relative").css("margin-top", "0").hide();
            $("ul", this).width(x)
        })
    };
    return {
        init: function () {
            v();
            t();
            u();
            f();
            d();
            h();
            e();
            i();
            k();
            j();
            a();
            p()
        },
        getLayoutColorCode: function (x) {
            if (m[x]) {
                return m[x]
            } else {
                return ""
            }
        },
        blockUI: function (x, y) {
            var x = $(x);
            x.block({
                message: '<img src="./assets/img/ajax-loading.gif" alt="">',
                centerY: y != undefined ? y : true,
                css: {
                    top: "10%",
                    border: "none",
                    padding: "2px",
                    backgroundColor: "none"
                },
                overlayCSS: {
                    backgroundColor: "#000",
                    opacity: 0.05,
                    cursor: "wait"
                }
            })
        },
        unblockUI: function (x) {
            $(x).unblock({
                onUnblock: function () {
                    $(x).removeAttr("style")
                }
            })
        }
    }
}();