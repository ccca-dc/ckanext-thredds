// Enable JavaScript's strict mode. Strict mode catches some common
// programming errors and throws exceptions, prevents some unsafe actions from
// being taken, and disables some confusing and bad JavaScript features.
"use strict";


ckan.module('subset_datepicker', function (jQuery, _) {
  return {
    options: {
        year_start: 1950,
        year_end: 2100
    },

    initialize: function () {
    //  console.log("Date initialized for element: ", this.el);
    //  (this.el).datepicker({ 'date-format': 'yy/mm/dd'}); //datepicker
      (this.el).datetimepicker({ 'yearStart': this.options.year_start, 'yearEnd': this.options.year_end }); //datepicker


      $.proxyAll(this, /_on/);


    }, // initialize
  }; // return
}); //ckan_module
