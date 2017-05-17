// Enable JavaScript's strict mode. Strict mode catches some common
// programming errors and throws exceptions, prevents some unsafe actions from
// being taken, and disables some confusing and bad JavaScript features.
"use strict";


ckan.module('subset_datepicker', function (jQuery, _) {
  return {
    initialize: function () {
    //  console.log("Date initialized for element: ", this.el);
    //  (this.el).datepicker({ 'date-format': 'yy/mm/dd'}); //datepicker
      (this.el).datetimepicker(); //datepicker


      $.proxyAll(this, /_on/);


    }, // initialize
  }; // return
}); //ckan_module
