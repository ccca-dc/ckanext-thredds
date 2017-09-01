"use strict";

ckan.module('stored_queries', function($) {
  return {
    /* options object can be extended using data-module-* attributes */
    options: {
      user_queries: "",
      all_queries: ""
    },

    initialize: function () {
      $.proxyAll(this, /_on/);
      var options = this.options;
      var user_queries = options.user_queries;
      this.all_queries = options.all_queries;
      this.el.on('click', this._onClick);
    },

    _onClick: function(event) {
        var _fillFields = function(element) {
            var valQuoteChange = element.find('div:first').attr("value").replace(/'/g, '"');
            params = JSON.parse(valQuoteChange);
            for (param in params) {
                //if (params[param].match(/[a-z]/i)){
                    if(param == "north"){
                        $('#southWest').show();
                        $('label[for="north"]').text("North");
                        $('label[for="east"]').text("East");

                        $('#north').val(params[param]);

                        document.getElementById("radio_netcdf").checked=true;
                        document.getElementById("radio_csv").disabled=true;
                        document.getElementById("radio_xml").disabled=true;
                    } else if(param == "latitude"){
                        $('#south').val("");
                        $('#west').val("");
                        $('#southWest').hide();
                        $('label[for="north"]').text("Latitude");
                        $('label[for="east"]').text("Longitude");

                        $('#north').val(params[param]);

                        document.getElementById("radio_csv").disabled=false;
                        document.getElementById("radio_xml").disabled=false;
                    } else if(param == "longitude"){
                        $('#east').val(params[param]);
                    }
                    else if($("[name='" + param + "']").is(':radio') != true){
                        $("[name='" + param + "']").val(params[param]);
                    }else{
                        for (j = 0; j < $("[name='" + param + "']").length; j++) {
                            if($("[name='" + param + "']")[j].value.toLowerCase() ==params[param]){
                                $("[name='" + param + "']")[j].checked=true;
                            }
                        }
                    }
                }
            };

        if(this.el.attr("id") != "other_queries"){
            _fillFields(this.el);
        }else{
            var all_queries = JSON.parse(this.all_queries.replace(/'/g, '"'));
            this.el.text("");
            this.el.append($('<h5 name="dropdown_heading">Other Public Queries: <span class="badge">' + all_queries.length + '</span></h5>'));
            for (var i = 0; i < all_queries.length; i++) {
                var li = '<li name="pubQuery"><a href="#">\
                          <div value="' + JSON.stringify(all_queries[i]).replace(/"/g, "'") +'"><h5>\
                          '+ all_queries[i]['name'] + '\
                          <br><small>\
                          '+ all_queries[i]['format'];
                if(all_queries[i]['north']){
                    li += ', ' + all_queries[i]['north'] + '/';
                    li += all_queries[i]['east'] + '/';
                    li += all_queries[i]['south'] + '/';
                    li += all_queries[i]['west'];
                } else if(all_queries[i]['latitude']){
                    li += ', ' + all_queries[i]['latitude'] + '/';
                    li += all_queries[i]['longitude'];
                }
                if(all_queries[i]['time_start']){
                    li += ', ' + moment(new Date(all_queries[i]['time_start'])).format("YYYY-MM-DD hh:mm:ss") + ' - ';
                    li += moment(new Date(all_queries[i]['time_end'])).format("YYYY-MM-DD hh:mm:ss");
                }
                li += '<br><span class="badge">created: ' + moment(new Date(all_queries[i]['created'])).format("YYYY-MM-DD hh:mm:ss") + '</span>';
                $('ul#querylist').append($(li));
            }
            $('li[name = "pubQuery"]').click(function(e){
                _fillFields($(this));
            });
        }
    }
}});
