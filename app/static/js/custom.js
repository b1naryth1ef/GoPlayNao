"use strict";
$(document).ready(function () {
    // $(".sidebar-search").submit(function (a) {
    //     $(".sidebar-search-results").slideDown(200);
    //     return false
    // });
    // $(".sidebar-search-results .close").click(function () {
    //     $(".sidebar-search-results").slideUp(200)
    // });
    $(".row-bg-toggle").click(function (a) {
        a.preventDefault();
        $(".row.row-bg").each(function () {
            $(this).slideToggle(200)
        })
    });
    $("#sparkline-bar").sparkline("html", {
        type: "bar",
        height: "35px",
        zeroAxis: false,
        barColor: App.getLayoutColorCode("red")
    });
    $("#sparkline-bar2").sparkline("html", {
        type: "bar",
        height: "35px",
        zeroAxis: false,
        barColor: App.getLayoutColorCode("green")
    });
    $(".widget .toolbar .widget-refresh").click(function () {
        var a = $(this).parents(".widget");
        App.blockUI(a);
        window.setTimeout(function () {
            App.unblockUI(a);
            noty({
                text: "<strong>Widget updated.</strong>",
                type: "success",
                timeout: 1000
            })
        }, 1000)
    });
    setTimeout(function () {
        $("#sidebar .notifications.demo-slide-in > li:eq(1)").slideDown(500)
    }, 3500);
    setTimeout(function () {
        $("#sidebar .notifications.demo-slide-in > li:eq(0)").slideDown(500)
    }, 7000)
});