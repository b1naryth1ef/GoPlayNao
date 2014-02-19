var Plugins = function () {
    var g = function () {
        $.browser = {};
        (function () {
            $.browser.msie = false;
            $.browser.version = 0;
            if (navigator.userAgent.match(/MSIE ([0-9]+)\./)) {
                $.browser.msie = true;
                $.browser.version = RegExp.$1
            }
        })()
    };
    var i = function () {
        if ($.fn.daterangepicker) {
            $(".range").daterangepicker({
                startDate: moment().subtract("days", 29),
                endDate: moment(),
                minDate: "01/01/2012",
                maxDate: "12/31/2014",
                dateLimit: {
                    days: 60
                },
                showDropdowns: true,
                showWeekNumbers: true,
                timePicker: false,
                timePickerIncrement: 1,
                timePicker12Hour: true,
                ranges: {
                    Today: [moment(), moment()],
                    Yesterday: [moment().subtract("days", 1), moment().subtract("days", 1)],
                    "Last 7 Days": [moment().subtract("days", 6), moment()],
                    "Last 30 Days": [moment().subtract("days", 29), moment()],
                    "This Month": [moment().startOf("month"), moment().endOf("month")],
                    "Last Month": [moment().subtract("month", 1).startOf("month"), moment().subtract("month", 1).endOf("month")]
                },
                opens: "left",
                buttonClasses: ["btn btn-default"],
                applyClass: "btn-sm btn-primary",
                cancelClass: "btn-sm",
                format: "MM/DD/YYYY",
                separator: " to ",
                locale: {
                    applyLabel: "Submit",
                    fromLabel: "From",
                    toLabel: "To",
                    customRangeLabel: "Custom Range",
                    daysOfWeek: ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"],
                    monthNames: ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"],
                    firstDay: 1
                }
            }, function (q, o) {
                var p = q.format("MMMM D, YYYY") + " - " + o.format("MMMM D, YYYY");
                App.blockUI($("#content"));
                setTimeout(function () {
                    App.unblockUI($("#content"));
                    noty({
                        text: "<strong>Dashboard updated to " + p + ".</strong>",
                        type: "success",
                        timeout: 1000
                    })
                }, 1000);
                $(".range span").html(p)
            });
            $(".range span").html(moment().subtract("days", 29).format("MMMM D, YYYY") + " - " + moment().format("MMMM D, YYYY"))
        }
    };
    var k = function () {
        if ($.fn.sparkline) {
            $.extend(true, $.fn.sparkline.defaults, {
                line: {
                    highlightSpotColor: App.getLayoutColorCode("green"),
                    highlightLineColor: App.getLayoutColorCode("red")
                },
                bar: {
                    barColor: App.getLayoutColorCode("blue"),
                    negBarColor: App.getLayoutColorCode("red"),
                    barWidth: 5,
                    barSpacing: 2
                },
                tristate: {
                    posBarColor: App.getLayoutColorCode("green"),
                    negBarColor: App.getLayoutColorCode("red")
                },
                box: {
                    medianColor: App.getLayoutColorCode("red")
                }
            });
            $(window).resize(function () {
                $.sparkline_display_visible()
            }).resize();
            $(".statbox-sparkline").each(function () {
                $(this).sparkline("html", Plugins.getSparklineStatboxDefaults())
            })
        }
    };
    var l = function () {
        $.extend(true, $.fn.tooltip.defaults, {
            container: "body"
        });
        $(".bs-tooltip").tooltip({
            container: "body"
        });
        $(".bs-focus-tooltip").tooltip({
            trigger: "focus",
            container: "body"
        })
    };
    var h = function () {
        $(".bs-popover").popover()
    };
    var d = function () {
        if ($.noty) {
            $.extend(true, $.noty.defaults, {
                type: "alert",
                timeout: false,
                maxVisible: 5,
                animation: {
                    open: {
                        height: "toggle"
                    },
                    close: {
                        height: "toggle"
                    },
                    easing: "swing",
                    speed: 200
                }
            })
        }
    };
    var c = function () {
        if ($.easyPieChart) {
            $.extend(true, $.easyPieChart.defaultOptions, {
                lineCap: "butt",
                animate: 500,
                barColor: App.getLayoutColorCode("blue")
            });
            $(".circular-chart").easyPieChart({
                size: 110,
                lineWidth: 10
            })
        }
    };
    var m = function () {
        if ($.fn.dataTable) {
            $.extend(true, $.fn.dataTable.defaults, {
                oLanguage: {
                    sSearch: ""
                },
                sDom: "<'row'<'dataTables_header clearfix'<'col-md-6'l><'col-md-6'f>r>>t<'row'<'dataTables_footer clearfix'<'col-md-6'i><'col-md-6'p>>>",
                iDisplayLength: 5,
                fnDrawCallback: function () {
                    if ($.fn.uniform) {
                        $(":radio.uniform, :checkbox.uniform").uniform()
                    }
                    if ($.fn.select2) {
                        $(".dataTables_length select").select2({
                            minimumResultsForSearch: "-1"
                        })
                    }
                    var o = $(this).closest(".dataTables_wrapper").find("div[id$=_filter] input");
                    if (o.parent().hasClass("input-group")) {
                        return
                    }
                    o.addClass("form-control");
                    o.wrap('<div class="input-group"></div>');
                    o.parent().prepend('<span class="input-group-addon"><i class="icon-search"></i></span>')
                }
            });
            $.fn.dataTable.defaults.aLengthMenu = [
                [5, 10, 25, 50, -1],
                [5, 10, 25, 50, "All"]
            ];
            $(".datatable").each(function () {
                var w = $(this);
                var y = {};
                var s = w.data("datatable");
                if (typeof s != "undefined") {
                    $.extend(true, y, s)
                }
                var x = w.data("displayLength");
                if (typeof x != "undefined") {
                    $.extend(true, y, {
                        iDisplayLength: x
                    })
                }
                var r = w.data("horizontalWidth");
                if (typeof r != "undefined") {
                    $.extend(true, y, {
                        sScrollX: "100%",
                        sScrollXInner: r,
                        bScrollCollapse: true
                    })
                }
                if (w.hasClass("table-checkable")) {
                    $.extend(true, y, {
                        aoColumnDefs: [{
                            bSortable: false,
                            aTargets: [0]
                        }]
                    })
                }
                if (w.hasClass("table-tabletools")) {
                    $.extend(true, y, {
                        sDom: "<'row'<'dataTables_header clearfix'<'col-md-4'l><'col-md-8'Tf>r>>t<'row'<'dataTables_footer clearfix'<'col-md-6'i><'col-md-6'p>>>",
                        oTableTools: {
                            aButtons: ["copy", "print", "csv", "xls", "pdf"],
                            sSwfPath: "plugins/datatables/tabletools/swf/copy_csv_xls_pdf.swf"
                        }
                    })
                }
                if (w.hasClass("table-colvis")) {
                    $.extend(true, y, {
                        sDom: "<'row'<'dataTables_header clearfix'<'col-md-6'l><'col-md-6'Cf>r>>t<'row'<'dataTables_footer clearfix'<'col-md-6'i><'col-md-6'p>>>",
                        oColVis: {
                            buttonText: "Columns <i class='icon-angle-down'></i>",
                            iOverlayFade: 0
                        }
                    })
                }
                if (w.hasClass("table-tabletools") && w.hasClass("table-colvis")) {
                    $.extend(true, y, {
                        sDom: "<'row'<'dataTables_header clearfix'<'col-md-6'l><'col-md-6'TCf>r>>t<'row'<'dataTables_footer clearfix'<'col-md-6'i><'col-md-6'p>>>",
                    })
                }
                if (w.hasClass("table-checkable") && w.hasClass("table-colvis")) {
                    $.extend(true, y, {
                        oColVis: {
                            aiExclude: [0]
                        }
                    })
                }
                if (w.hasClass("table-responsive")) {
                    var q;
                    var p = {
                        tablet: 1024,
                        phone: 480
                    };
                    var t = $.fn.dataTable.defaults.fnDrawCallback;
                    $.extend(true, y, {
                        bAutoWidth: false,
                        fnPreDrawCallback: function () {
                            if (!q) {
                                q = new ResponsiveDatatablesHelper(this, p)
                            }
                        },
                        fnRowCallback: function (C, B, A, z) {
                            q.createExpandIcon(C)
                        },
                        fnDrawCallback: function (z) {
                            t.apply(this, z);
                            q.respond()
                        }
                    })
                }
                var v = w.data("datatableFunction");
                if (typeof v != "undefined") {
                    $.extend(true, y, window[v]())
                }
                if (w.hasClass("table-columnfilter")) {
                    var u = {};
                    var o = w.data("columnfilter");
                    if (typeof o != "undefined") {
                        $.extend(true, u, o)
                    }
                    $(this).dataTable(y).columnFilter(u);
                    w.find(".filter_column").each(function () {
                        var z = w.data("columnfilterSelect2");
                        if (typeof z != "undefined") {
                            $(this).children("input").addClass("form-control");
                            $(this).children("select").addClass("full-width-fix").select2({
                                placeholderOption: "first"
                            })
                        } else {
                            $(this).children("input, select").addClass("form-control")
                        }
                    })
                } else {
                    $(this).dataTable(y)
                }
            })
        }
    };
    var j = {
        colors: [App.getLayoutColorCode("blue"), App.getLayoutColorCode("red"), App.getLayoutColorCode("green"), App.getLayoutColorCode("purple"), App.getLayoutColorCode("grey"), App.getLayoutColorCode("yellow")],
        legend: {
            show: true,
            labelBoxBorderColor: "",
            backgroundOpacity: 0.95
        },
        series: {
            points: {
                show: false,
                radius: 3,
                lineWidth: 2,
                fill: true,
                fillColor: "#ffffff",
                symbol: "circle"
            },
            lines: {
                show: true,
                lineWidth: 2,
                fill: false,
                fillColor: {
                    colors: [{
                        opacity: 0.4
                    }, {
                        opacity: 0.1
                    }]
                },
            },
            bars: {
                lineWidth: 1,
                barWidth: 1,
                fill: true,
                fillColor: {
                    colors: [{
                        opacity: 0.7
                    }, {
                        opacity: 1
                    }]
                },
                align: "left",
                horizontal: false
            },
            pie: {
                show: false,
                radius: 1,
                label: {
                    show: false,
                    radius: 2 / 3,
                    formatter: function (o, p) {
                        return '<div style="font-size:8pt;text-align:center;padding:2px;color:white;text-shadow: 0 1px 0 rgba(0, 0, 0, 0.6);">' + o + "<br/>" + Math.round(p.percent) + "%</div>"
                    },
                    threshold: 0.1
                }
            },
            shadowSize: 0
        },
        grid: {
            show: true,
            borderColor: "#efefef",
            tickColor: "rgba(0,0,0,0.06)",
            labelMargin: 10,
            axisMargin: 8,
            borderWidth: 0,
            minBorderMargin: 10,
            mouseActiveRadius: 5
        },
        tooltipOpts: {
            defaultTheme: false
        },
        selection: {
            color: App.getLayoutColorCode("blue")
        }
    };
    var b = {
        colors: ["#ffffff"],
        legend: {
            show: false,
            backgroundOpacity: 0
        },
        series: {
            points: {}
        },
        grid: {
            tickColor: "rgba(255, 255, 255, 0.1)",
            color: "#ffffff",
        },
        shadowSize: 1
    };
    var f = function () {
        if ($.fn.knob) {
            $(".knob").knob();
            $(".knob").each(function () {
                if (typeof $(this).attr("data-fgColor") == "undefined") {
                    $(this).trigger("configure", {
                        fgColor: App.getLayoutColorCode("blue"),
                        inputColor: App.getLayoutColorCode("blue")
                    })
                }
            })
        }
    };
    var n = {
        type: "bar",
        height: "19px",
        zeroAxis: false,
        barWidth: "4px",
        barSpacing: "1px",
        barColor: "#fff"
    };
    var e = function () {
        if ($.fn.colorpicker) {
            $(".bs-colorpicker").colorpicker()
        }
    };
    var a = function () {
        if ($.fn.template) {
            $.extend(true, $.fn.template.defaults, {})
        }
    };
    return {
        init: function () {
            g();
            i();
            k();
            l();
            h();
            d();
            m();
            c();
            f();
            e()
        },
        getFlotDefaults: function () {
            return j
        },
        getFlotWidgetDefaults: function () {
            return $.extend(true, {}, Plugins.getFlotDefaults(), b)
        },
        getSparklineStatboxDefaults: function () {
            return n
        }
    }
}();