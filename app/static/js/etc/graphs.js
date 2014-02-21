
function graph_drawPlayerOverview(data, el) {
    var result = []
    _.each(data, function (v, k) {
        if (k === "skill") {
            color = App.getLayoutColorCode("greem")
        } else if (k === "kd") {
            color = App.getLayoutColorCode("red")
        }
        result.push({
            "label": "Player "+k,
            "data": v,
            "color": color
        })
    })

    $.plot(el, result, $.extend(true, {}, Plugins.getFlotWidgetDefaults(), {
        xaxis: {
            mode: "time",
            tickSize: [1, "day"],
            tickLength: 0
        },
        series: {
            lines: {
                fill: false,
                lineWidth: 1.5
            },
            points: {
                show: true,
                radius: 4,
                lineWidth: 1.1
            },
            grow: {
                active: true,
                growings: [{
                    stepMode: "maximum"
                }]
            }
        },
        grid: {
            hoverable: true,
            clickable: true
        },
        tooltip: true,
        tooltipOpts: {
            content: "%s: %y"
        }
    }))
}