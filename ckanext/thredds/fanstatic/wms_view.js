ckan.module('wms_view', function ($) {
  return {
      /* options object can be extended using data-module-* attributes */
      options: {
          resource_id:'',
          subset_params:'',
          spatial_params:'',
          vertical_data:'',
          vertical_level:'',
          default_level:'',
          site_url:'',
          minimum:'',
          maximum:'',
          num_colorbands:'',
          logscale:'',
          default_layer:'',
          default_colormap:''
      }, //options

      initialize: function () {
        $.proxyAll(this, /_on/);
        var self = this;

        var options = this.options;

        this.sandbox = ckan.sandbox();

        this.sandbox.client.call('GET','thredds_get_layers',
                                '?id='+ options.resource_id,
                                 this._onHandleData,
                                 this._onHandleError
                                );

      }, //initialize

      initializePreview: function () {
        var startDate = new Date();
        startDate.setUTCHours(0, 0, 0, 0);

        var self = this;
        var wmslayers = $.map(self.options.layers, function( value, key ) { return value.children});
        var wmslayers_id = $.map(wmslayers, function( value, key ) { return value.id});
        var wmsabstracts = $.map(self.options.layers, function( value, key ) { return value.label } );

        if (self.options.logscale){
          if (self.options.logscale=="True")
            var wmslogscale = true;
          else
            var wmslogscale = false;
        }
        else {
          var wmslogscale = false;
        }

        if ($.isNumeric(self.options.default_layer)) {
          var wmslayer_selected = wmslayers[self.options.default_layer];
          if (wmsabstracts.length > self.options.default_layer)
            var wmsabstract_selected = wmsabstracts[self.options.default_layer];
          else
            var wmsabstract_selected = wmsabstracts[0];
        } else {
          var wmslayer_selected = wmslayers[0];
          var wmsabstract_selected = wmsabstracts[0];
        }
        var vertical_level_selected = 0;
        if (self.options.vertical_data){
              var vertical_levels = self.options.vertical_data['values'];
              var vertical_level_values = $.map(vertical_levels, function( value, key ) { return value.value});
              var vertical_level_names = $.map(vertical_levels, function( value, key ) { return (value.name).toString()});
        }
        if (self.options.default_level) {
            if ($.isNumeric(self.options.default_level))
              vertical_level_selected = self.options.default_level;
            else
              vertical_level_selected = parseInt(self.options.default_level);
        } else {
          vertical_level_selected = 0;
        }

        if ($.type(self.options.default_colormap) == "string") {
          var palette_selection = self.options.default_colormap;
        } else {
          var palette_selection = self.options.layers_details.defaultPalette;
        }

        var style_selection = self.options.layers_details.supportedStyles[0];


        if ($.isNumeric(self.options.num_colorbands)) {
          var num_colorbands = self.options.num_colorbands;
        } else {
          var num_colorbands = 100;
        }


        var opacity = 1;

        // check and store subset for subset_view
        var subset_json = self.options.spatial_params;
        var subset_parameter = self.options.subset_params;
        var subset_bounds ='';
        var subset_times = '';

        if (subset_parameter != ''){
          southWest = L.latLng(self.options.subset_params['south'],  self.options.subset_params['west']);
          northEast = L.latLng(self.options.subset_params['north'], self.options.subset_params['east']);

          subset_bounds = L.latLngBounds(southWest, northEast);
          subset_times = subset_parameter['time_start'] +"/" + subset_parameter['time_end'];

          // Attention: Necessary Format!
          //subset_times = "2018-04-12T12:00:00Z" +"/" + "2018-04-13T12:00:00Z";
        }

        // Check if time in resource
        // Anja 29.6.18: Thre maybe a better method;
        // but so far nearestTimeIso seems to indicate that the time is there bzw here ;-)
        var time_included = true;

        if ('nearestTimeIso' in self.options.layers_details){
              time_included = true;

        }
        else {
            time_included = false;
        }


        if (subset_times != ''){
          var map = L.map('map', {
              zoom: 7,
              fullscreenControl: true,
              timeDimensionControl: time_included,
              timeDimensionControlOptions: {
                  position: 'bottomleft',
                  playerOptions: {
                      transitionTime: 1000
                  },
                  minSpeed: 0.1,
                  maxSpeed: 2.0
              },
              timeDimension: time_included,
              timeDimensionOptions: {
                  timeInterval:subset_times,
                  //period: "P1DT1H" // Defines (the Format of) the time period
                   period: "PT1H" // Defines (the Format of) the time period
                 },
              center: [47.3, 13.9]
          }); //map
        }
        else {
          var map = L.map('map', {
              zoom: 7,
              fullscreenControl: true,
              timeDimensionControl: time_included,
              timeDimensionControlOptions: {
                  position: 'bottomleft',
                  playerOptions: {
                      transitionTime: 1000
                  },
                  minSpeed: 0.1,
                  maxSpeed: 2.0
              },
              timeDimension: time_included,
              center: [47.3, 13.9]
          }); //map
        }


        // check whether to adapt view extend
        var spatial_params = self.options.spatial_params;
        var spatial_bounds ='';
        if ((spatial_params != '') && (spatial_params != "")){
          if (spatial_params['type']){ // for some reasons or others spatial_params have value 'true' if empty
              var multipolygon = L.geoJson(spatial_params);
              spatial_bounds = multipolygon.getBounds();
              var center = spatial_bounds.getCenter();
              //multipolygon.addTo(map); // Anja, 28.6.18 This will add a blue rectangle marking the spatial extend - might be nice too :-)
              map.fitBounds(spatial_bounds);
              map.panTo(center);
              //map.fitWorld();
          }
        }

          // Set min/max; if empty according to map/subset
          if (($.isNumeric(self.options.minimum)) &&  ($.isNumeric(self.options.maximum)) ) {
            var min_value = self.options.minimum.toString();
            var max_value = self.options.maximum.toString();
          } else {
                var min_value = '';
                var max_value = '';
                if (subset_bounds){
                    var bbox = subset_bounds.getWest() + ','
                            + subset_bounds.getSouth() + ','
                            + subset_bounds.getEast() + ','
                             +subset_bounds.getNorth()
                    }
                 else
                    var bbox = self.options.layers_details.bbox;

                //GET MIN MAX
                if (self.options.vertical_data){
                  self.sandbox.client.call('GET','thredds_get_minmax',
                                      '?SERVICE=WMS&VERSION=1.1.1&SRS=EPSG:4326' + // Attention -copied from leaflet! Anja, 9.7
                                      '&bbox='+ bbox +
                                      '&width=50'+
                                      '&height=50'+
                                      '&id='+ self.options.resource_id +
                                      '&layers=' + wmslayer_selected.id +
                                      '&elevation=' + vertical_level_values[vertical_level_selected],
                                       self._onHandleMinMax,
                                       self._onHandleError
                                      );
                  }
                else{
                  self.sandbox.client.call('GET','thredds_get_minmax',
                                       '?SERVICE=WMS&VERSION=1.1.1&SRS=EPSG:4326' + // Attention -copied from leaflet! Anja, 9.7
                                       '&bbox='+ bbox +
                                       '&width=50'+
                                       '&height=50'+
                                        '&id='+ self.options.resource_id +
                                        '&layers=' + wmslayer_selected.id,
                                         self._onHandleMinMax,
                                         self._onHandleError
                                        );
              }
          }

        // ------------------------------------------------
        // Create control elements for wms_view (wms_form is separate!)
        // Layer


        $( "#layer" ).append(
            this._getDropDownList(
                'layers','select-layers',wmslayers_id, wmslayer_selected.id)
        );

        if (self.options.vertical_data){
              $( "#vertical_level" ).append(
                this._getDropDownList(
                    'vertical_levels','select-level',vertical_level_values, vertical_level_values[vertical_level_selected])
            );
        }

        $( "#logscale-field" ).append(
            this._getDropDownList(
                'select-logscale','select-logscale',{"true":true, "false":false}, wmslogscale.toString())

        );

        // Style
        $( "#style" ).append(
          this._getDropDownList(
              'styles','select-styles',self.options.layers_details.supportedStyles.sort(),'')
        );

        // Palette
        $( "#palette" ).append(
          this._getDropDownList(
              'palettes','select-palettes',self.options.layers_details.palettes.sort(),'')
        );

        // Minimum/Maximum
        $( "#min-field" ).append(
          $("<input id='min-value' type='text' class='numbersOnly form-control' value=" + min_value + ">")
        );
        $( "#max-field" ).append(
          $("<input id='max-value' type='text' class='numbersOnly form-control' value=" + max_value + ">")
        );

        //Colors
        $( "#num-colorband" ).append(
          $("<input id='num-colorbands' type='text' class='numbersOnly form-control' value=" + num_colorbands + ">")
        );

        // Opacity
        $( "#opacity-pane" ).append(
          $("<input id='opacity-value' type='range' min='0' max='1' step='0.1' value=" + opacity.toString() + " />")
        );

        // Export
        $( "#export-pane" ).append(
          $("<button class='btn btn-primary' type='button' id='export-png'>Export Map to PNG</button>")
        );
        // ------------------------------------------------
        // Define functions for control elements
        $('.numbersOnly').keyup(function () {
            this.value = this.value.replace(/[^0-9\.\-\+]/g,'');
        });

        $('#min-value').on('focusout', function() {
          min_value = this.value;
          // Update Preview
          // cccaHeightLayer.setParams({colorscalerange: min_value + ',' + max_value});
          cccaHeightTimeLayer.setParams({colorscalerange: min_value + ',' + max_value});
          cccaLegend.removeFrom(map);
          cccaLegend.addTo(map);
        });

        $('#max-value').on('focusout', function() {
          max_value = this.value;
          // Update Preview
          // cccaHeightLayer.setParams({colorscalerange: min_value + ',' + max_value});
          cccaHeightTimeLayer.setParams({colorscalerange: min_value + ',' + max_value});
          cccaLegend.removeFrom(map);
          cccaLegend.addTo(map);
        });

        $('#num-colorbands').on('focusout', function() {
          num_colorbands = this.value;
          // Update Preview
          // cccaHeightLayer.setParams({colorscalerange: min_value + ',' + max_value});
          cccaHeightTimeLayer.setParams({numcolorbands: num_colorbands});
          cccaLegend.removeFrom(map);
          cccaLegend.addTo(map);
        });

        $('#select-palettes').on('change', function() {
          palette_selection = this.value;
          // Update Preview
          // cccaHeightLayer.setParams({styles:style_selection + '/' + palette_selection});
          cccaHeightTimeLayer.setParams({styles:style_selection + '/' + palette_selection});
          cccaLegend.removeFrom(map);
          cccaLegend.addTo(map);
        });

        $('#select-styles').on('change', function() {
          style_selection = this.value;
          // Update Preview
          // cccaHeightLayer.setParams({styles:style_selection + '/' + palette_selection});
          cccaHeightTimeLayer.setParams({styles:style_selection + '/' + palette_selection});
          cccaLegend.removeFrom(map);
          cccaLegend.addTo(map);
        });

        $('#select-layers').on('change', function() {
            index = this.selectedIndex;
            wmslayer_selected = wmslayers[index];
            wmsabstract_selected = wmsabstracts[index];
            // Get and adapt min max_value
            //this.sandbox = ckan.sandbox();
            var bbox = map.getBounds().getWest() + ','
                    + map.getBounds().getSouth() + ','
                    + map.getBounds().getEast() + ','
                     + map.getBounds().getNorth()
            if (self.options.vertical_data){
              self.sandbox.client.call('GET','thredds_get_minmax',
                                  '?SERVICE=WMS&VERSION=1.1.1&SRS=EPSG:4326' + // Attention -copied from leaflet! Anja, 9.7
                                  '&bbox='+ bbox +
                                  '&width=50'+
                                  '&height=50'+
                                  '&id='+ self.options.resource_id +
                                  '&layers=' + wmslayer_selected.id +
                                  '&elevation=' + vertical_level_values[vertical_level_selected],
                                   self._onHandleMinMax,
                                   self._onHandleError
                                  );
                // Update View - Done - in minmax
                //cccaHeightTimeLayer.setParams({layers:wmslayer_selected.id, elevation:vertical_level_values[vertical_level_selected]});
                //cccaLegend.removeFrom(map);
                //cccaLegend.addTo(map);
              }
            else{
              self.sandbox.client.call('GET','thredds_get_minmax',
                                   '?SERVICE=WMS&VERSION=1.1.1&SRS=EPSG:4326' + // Attention -copied from leaflet! Anja, 9.7
                                   '&bbox='+ bbox +
                                   '&width=50'+
                                   '&height=50'+
                                    '&id='+ self.options.resource_id +
                                    '&layers=' + wmslayer_selected.id,
                                     self._onHandleMinMax,
                                     self._onHandleError
                                    );
                // Update View Done in MinmAx
                //cccaHeightTimeLayer.setParams({layers:wmslayer_selected.id});
                //cccaLegend.removeFrom(map);
                //cccaLegend.addTo(map);
            }

        });

        $('#select-level').on('change', function() {
            index = this.selectedIndex;
            vertical_level_selected = index;
            // Get and adapt min max_value
            //this.sandbox = ckan.sandbox();
            var bbox = map.getBounds().getWest() + ','
                    + map.getBounds().getSouth() + ','
                    + map.getBounds().getEast() + ','
                     + map.getBounds().getNorth();
             self.sandbox.client.call('GET','thredds_get_minmax',
                                 '?SERVICE=WMS&VERSION=1.1.1&SRS=EPSG:4326' + // Attention -copied from leaflet! Anja, 9.7
                                 '&bbox='+ bbox +
                                 '&width=50'+ // not sure what this does ...
                                 '&height=50'+ // not sure what this does ...
                                 '&id='+ self.options.resource_id +
                                 '&layers=' + wmslayer_selected.id +
                                 '&elevation=' + vertical_level_values[vertical_level_selected],
                                  self._onHandleMinMax,
                                  self._onHandleError
                                 );
               // Update View - Done in min/max
              // cccaHeightTimeLayer.setParams({layers:wmslayer_selected.id, elevation:vertical_level_values[vertical_level_selected]});
              // cccaLegend.removeFrom(map);
              // cccaLegend.addTo(map);
        });

        $('#opacity-value').on('change', function() {
          opacity = this.value;
          // Update Preview
          cccaHeightTimeLayer.setOpacity(opacity);

        });

        $('#select-logscale').on('change', function() {
          wmslogscale = this.value;
          // Update Preview
          cccaHeightTimeLayer.setParams({logscale:wmslogscale});
          cccaLegend.removeFrom(map);
          cccaLegend.addTo(map);
      });

        $('#export-png').on('click', function() {
            var mapPane = $(".leaflet-map-pane")[0];
            //var mapTransform = mapPane.style.transform.split(",");
            //var mapX = parseFloat(mapTransform[0].split("(")[1].replace("px", ""));
            //var mapY = parseFloat(mapTransform[1].replace("px", ""));
            var mapX = 0;
            var mapY = 0;
            mapPane.style.transform = "";
            mapPane.style.left = mapX + "px";
            mapPane.style.top = mapY + "px";

            var myTiles = $("img.leaflet-tile");
            var tilesLeft = [];
            var tilesTop = [];
            var tileMethod = [];
            for (var i = 0; i < myTiles.length; i++) {
                if (myTiles[i].style.left != "") {
                    tilesLeft.push(parseFloat(myTiles[i].style.left.replace("px", "")));
                    tilesTop.push(parseFloat(myTiles[i].style.top.replace("px", "")));
                    tileMethod[i] = "left";
                } else if (myTiles[i].style.transform != "") {
                    var tileTransform = myTiles[i].style.transform.split(",");
                    tilesLeft[i] = parseFloat(tileTransform[0].split("(")[1].replace("px", ""));
                    tilesTop[i] = parseFloat(tileTransform[1].replace("px", ""));
                    myTiles[i].style.transform = "";
                    tileMethod[i] = "transform";
                } else {
                    tilesLeft[i] = 0;
                    tilesRight[i] = 0;
                    tileMethod[i] = "neither";
                }
                myTiles[i].style.left = (tilesLeft[i]) + "px";
                myTiles[i].style.top = (tilesTop[i]) + "px";
                myTiles[i].style.opacity = myTiles[i]._layer.options.opacity;
            }

            var myDivicons = $(".leaflet-marker-icon");
            var dx = [];
            var dy = [];
            for (var i = 0; i < myDivicons.length; i++) {
                var curTransform = myDivicons[i].style.transform;
                var splitTransform = curTransform.split(",");
                dx.push(parseFloat(splitTransform[0].split("(")[1].replace("px", "")));
                dy.push(parseFloat(splitTransform[1].replace("px", "")));
                myDivicons[i].style.transform = "";
                myDivicons[i].style.left = dx[i] + "px";
                myDivicons[i].style.top = dy[i] + "px";
            }

            var mapWidth = parseFloat($("#map").css("width").replace("px", ""));
            var mapHeight = parseFloat($("#map").css("height").replace("px", ""));

            var linesLayer = $("svg.leaflet-zoom-animated")[0];
            if (linesLayer) {
                var oldLinesWidth = linesLayer.getAttribute("width");
                var oldLinesHeight = linesLayer.getAttribute("height");
                var oldViewbox = linesLayer.getAttribute("viewBox");
                linesLayer.setAttribute("width", mapWidth);
                linesLayer.setAttribute("height", mapHeight);
                linesLayer.setAttribute("viewBox", "0 0 " + mapWidth + " " + mapHeight);
                var linesTransform = linesLayer.style.transform.split(",");
                var linesX = parseFloat(linesTransform[0].split("(")[1].replace("px", ""));
                var linesY = parseFloat(linesTransform[1].replace("px", ""));
                linesLayer.style.transform = "";
                linesLayer.style.left = "";
                linesLayer.style.top = "";
            }
            $(".leaflet-top").hide();
            $(".leaflet-bar").hide();
            $(".leaflet-control-attribution").hide();
            var currentTime = new Date(cccaHeightTimeLayer._timeDimension.getCurrentTime());
            $(".leaflet-bottom.leaflet-left").append("<div id='export-info'><p>" + currentTime.toUTCString() + "</p><p>" + wmsabstracts + "</p></div>");
            //$(".leaflet-bottom.leaflet-left").;


            html2canvas(document.getElementById("map"), {
                useCORS: true,
                letterRendering: false,
                onrendered: function (canvas) {
                   // var context = canvas.getContext('2d');
                   // context.scale(2, 2);
                    window.open(canvas.toDataURL("image/png"));
                    //window.location = canvas.toDataURL("image/png");
                    $(".leaflet-top").show();
                    $(".leaflet-bar").show();
                    $(".leaflet-control-attribution").show();
                    $("#export-info").remove();
                } //html2canvas
            });

            for (var i = 0; i < myTiles.length; i++) {
                if (tileMethod[i] == "left") {
                    myTiles[i].style.left = (tilesLeft[i]) + "px";
                    myTiles[i].style.top = (tilesTop[i]) + "px";
                    myTiles[i].style.opacity = "";
                } else if (tileMethod[i] == "transform") {
                    myTiles[i].style.left = "";
                    myTiles[i].style.top = "";
                    myTiles[i].style.transform = "translate(" + tilesLeft[i] + "px, " + tilesTop[i] + "px)";
                    myTiles[i].style.opacity = "";
                } else {
                    myTiles[i].style.left = "0px";
                    myTiles[i].style.top = "0px";
                    myTiles[i].style.transform = "translate(0px, 0px)";
                    myTiles[i].style.opacity = "";
                }
            }
            for (var i = 0; i < myDivicons.length; i++) {
                myDivicons[i].style.transform = "translate(" + dx[i] + "px, " + dy[i] + "px)";
                myDivicons[i].style.left = "0px";
                myDivicons[i].style.top = "0px";
            }
            if (linesLayer) {
                linesLayer.style.transform = "translate(" + (linesX) + "px," + (linesY) + "px)";
                linesLayer.setAttribute("viewBox", oldViewbox);
                linesLayer.setAttribute("width", oldLinesWidth);
                linesLayer.setAttribute("height", oldLinesHeight);
            }
            mapPane.style.transform = "translate(" + (mapX) + "px," + (mapY) + "px)";
            mapPane.style.left = "";
            mapPane.style.top = "";
        }); // export-png
        //------------------------- END Control Elements --------------------


        var cccaWMS = self.options.site_url + "thredds/wms/ckan/" + [self.options.resource_id.slice(0,3), self.options.resource_id.slice(3,6), self.options.resource_id.slice(6)].join("/");

        var wmsOptions =  {
            layers: wmslayer_selected.id,
            format: 'image/png',
            transparent: true,
            logscale:wmslogscale,
            colorscalerange: min_value + ',' + max_value,
            abovemaxcolor: "extend",
            belowmincolor: "extend",
            numcolorbands: num_colorbands,
            styles: style_selection + '/' + palette_selection
        }

        var cccaHeightLayer = L.tileLayer.wms(cccaWMS,wmsOptions);

        var markers = [{
            name: 'Eisenstadt',
            position: [47.8452778, 16.5247223]
        }, {
            name: 'Klagenfurt',
            position: [46.63, 14.31]
        }, {
            name: 'Sankt Pölten',
            position: [48.1749279, 15.5860448]
        }, {
            name: 'Linz',
            position: [48.3058789, 14.2865628]
        }, {
            name: 'Salzburg',
            position: [47.7666667, 13.05]
        }, {
            name: 'Graz',
            position: [47.0796751, 15.4203249]
        }, {
            name: 'Bregenz',
            position: [47.502947, 9.7451841]
        }, {
            name: 'Innsbruck',
            position: [47.2654296, 11.3927685]
        }, {
            name: 'Vienna',
            position: [48.209, 16.37]
        }];

        // Check whether the markers are inside a potential subset or spatial extend
        var add_markers = [];

        if (subset_bounds != '') {

            //check if default marker within
            for (i=0; i <markers.length;i++) {
               if ((subset_bounds.contains(markers[i].position))){
                 add_markers.push(markers[i]);
                }
            }

            // add center marker if non so far
            if (add_markers.length == 0){

                var center = subset_bounds.getCenter();
                var element = {
                  name: "Subset Center",
                  position: [center.lat, center.lng]

                };

              add_markers.push(element);
           }
         }
        else if (spatial_bounds != '') {

              //check if default marker within
              for (i=0; i <markers.length;i++) {
                 if ((spatial_bounds.contains(markers[i].position))){
                   add_markers.push(markers[i]);
                  }
              }

              // add center marker
              if (add_markers.length == 0){

                  var center = spatial_bounds.getCenter();
                  var element = {
                    name: "Center",
                    position: [center.lat, center.lng]

                  };

                add_markers.push(element);
             }

        }else{
          add_markers = markers;
        }


        var time_options = {
            updateTimeDimension: true,
            markers: add_markers,
            name: wmsabstract_selected,
            legendname: wmslayer_selected.label,
            maxValues: 2000,
            units: self.options.layers_details.units,
            enableNewMarkers: true
        };

        if (time_included)
          var cccaHeightTimeLayer = L.timeDimension.layer.wms.timeseries(cccaHeightLayer, time_options);
        else
         var cccaHeightTimeLayer = cccaHeightLayer;


        var cccaLegend = L.control({
            position: 'bottomright'
        });

        cccaLegend.onAdd = function(map) {

          var src = cccaWMS + "?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetLegendGraphic&LAYER=" + wmslayer_selected.id + "&colorscalerange="+ min_value + ',' + max_value + "&PALETTE="+ palette_selection +"&numcolorbands="+num_colorbands+"&transparent=TRUE"+"&LOGSCALE="+wmslogscale;

          var div = L.DomUtil.create('div', 'info legend');
          div.innerHTML +=
              '<img src="' + src + '" alt="legend">';
          return div;
        }; // cccaLegend.onAdd


        var overlayMaps = {};
        overlayMaps[wmsabstract_selected.toString()] = cccaHeightTimeLayer;

        map.on('overlayadd', function(eventLayer) {
            if (eventLayer.name == wmsabstract_selected) {
                cccaLegend.addTo(this);
            }
        }); // map on overlayadd

        map.on('overlayremove', function(eventLayer) {
            if (eventLayer.name == wmsabstract_selected) {
                map.removeControl(cccaLegend);
            }
        }); // map on overlayremove

        //right mouse or equivalent
        map.on('contextmenu', function(event) {

          var allMarkersArray = []; // for marker objects
          var allChartsArray = []; // for charts


          var event_position = event.latlng;

          if (event_position) {
            event_position.lat = event_position.lat.toFixed(1);
            event_position.lng = event_position.lng.toFixed(1);
          }
          else
            return;

          //console.log("Event:");
          //console.log(event.latlng);
          //console.log (event_position);

          var series_ids=[];
          //find and remove circle marker layer  and identify chart series layer
          for (ml in map._layers){

               if (map._layers[ml]._labelMarker && map._layers[ml]._position) {
                 var marker_position = map._layers[ml]._position;
                 //console.log("Marker:");
                 //console.log(marker_position);
                if (typeof(marker_position.lat)== "number"){
                   marker_position.lat= map._layers[ml]._position.lat.toFixed(1);
                   marker_position.lng= map._layers[ml]._position.lng.toFixed(1);
                  }
                 // Note corresponding chart
                 if (marker_position.lat == event_position.lat && marker_position.lng == event_position.lng  && map._layers[ml]._serieId){

                   //console.log(map._layers[ml]._serieId);
                   series_ids.push(map._layers[ml]._serieId); // necessary to find series in charts
                   map.removeLayer(map._layers[ml]);
                 }

               }
               else if (map._layers[ml]._chart) {
                   allChartsArray.push(map._layers[ml]);
               }

         } // for

         if (series_ids.length > 0){
         // remove  chart series
               //console.log("Charts");
               for (i=0;i < allChartsArray.length;i++) {
                 //console.log(allChartsArray[i]);
                 if (allChartsArray[i]._chart.series){
                       for (j=0; j<allChartsArray[i]._chart.series.length ; j++){
                         //console.log(allChartsArray[i]._chart.series[j].userOptions.id);
                         if (allChartsArray[i]._chart.series[j].userOptions.id.indexOf(series_ids) >=0 )
                                  allChartsArray[i]._chart.series[j].remove();
                      } //for
                  } //if

                } //for

          } // if series

        }); // map on contextmenu


        var baseLayers = getCommonBaseLayers(map); // see baselayers.js

        L.control.layers(baseLayers, overlayMaps).addTo(map);

        ////////////////////////////
        // For Subset  extent

        if (subset_bounds != '') {
              var styles = {
                point:{
                  iconUrl: '/img/marker.png',
                  iconSize: [14, 25],
                  iconAnchor: [7, 25]
                },
                base_:{
                  color: '#B52',
                  weight: 2,
                  opacity: 0,
                  fillColor: '#FCF6CF',
                  fillOpacity: 0.8
                },
                default_:{
                  color: '#ffffff', //'#B52'
                  weight: 2,
                  opacity: 1,
                  fillColor: '#ffffff', //'#FCF6CF',
                  fillOpacity: 0.3
                }
              };

              var ckanIcon = L.Icon.extend({options: styles.point});

              // set extent to subset bounds - will become hole
              var extent = subset_json;

              // milky rest of the map: TODO set to spatial extend of orginal resource
              map.fitWorld();
              var bounds = map.getBounds();
              map.fitBounds(subset_bounds);

              var inversePolygon = createPolygonFromBounds(bounds);

              // defines a MultiPolygon with a hole - see Definition below
              extent.coordinates[0].push(inversePolygon.geometry.coordinates[0]);

              /* Definition Mulitpolygon
              {
                "type": "MultiPolygon",
                "coordinates": [
                  [
                    {polygon},
                    {hole},
                    {hole},
                    {hole}
                  ]
                ]
              }
              */

              // From ckanext_spatial
              if (extent.type == 'Polygon'
                && extent.coordinates[0].length == 5) {
                _coordinates = extent.coordinates[0]
                w = _coordinates[0][0];
                e = _coordinates[2][0];
                if (w >= 0 && e < 0) {
                  w_new = w
                  while (w_new > e) w_new -=360
                  for (var i = 0; i < _coordinates.length; i++) {
                    if (_coordinates[i][0] == w) {
                      _coordinates[i][0] = w_new
                    };
                  };
                  extent.coordinates[0] = _coordinates
                };
              };


              var extentLayer = L.geoJson(extent, {
                  style: styles.default_,
                  pointToLayer: function (feature, latLng) {
                    return new L.Marker(latLng, {icon: new ckanIcon})
                  }});

               extentLayer.addTo(map);

              if (extent.type == 'Point'){
                map.setView(L.latLng(extent.coordinates[1],extent.coordinates[0]), 9);
              } else {
                map.fitBounds(extentLayer.getBounds());
            }//else

      } //if subset

      cccaHeightTimeLayer.addTo(map);
      // Check Vertical
      if (self.options.vertical_data)
          cccaHeightTimeLayer.setParams({elevation:vertical_level_values[vertical_level_selected]});


      }, //initializePreview


      _onHandleDataDetails: function(json) {
        if (json.success) {
          self.options.layers_details = json.result;
          this.initializePreview();
        }
      }, //_onHandleDataDetails

      _onHandleData: function(json) {
        if (json.success) {
          self = this;
          self.options.layers = json.result;

          var wmslayers = $.map(json.result, function( value, key ) { return value.children});
          self.sandbox.client.call('GET','thredds_get_layerdetails',
                                  '?id='+ self.options.resource_id + '&layer=' + wmslayers[0].id,
                                   this._onHandleDataDetails,
                                   this._onHandleError
                                  );
        } //if

      }, // _onHandleData


      _onHandleMinMax: function(json) {
        if (json.success) {
          var mv = document.getElementById("min-value").value = json.result.min ;
          var mv = document.getElementById("max-value").value = json.result.max ;
          min_value = json.result.min;
          max_value = json.result.max;
          $('#min-value').trigger('focusout');
          $('#max-value').trigger('focusout');
        } //if

      }, // _onHandleMinMax

      _onHandleError: function(error) {
        document.getElementById("wms-view").innerHTML = "<h2>Please login to use this view</h2>";
        console.log(error);
        throw new Error("Something went badly wrong!");

      }, //_onHandleError

      _getDropDownList: function(name, id, optionList,selectedItem) {
          var combo = $("<select></select>").attr("id", id).attr("name", name).attr("class","form-control");

          $.each(optionList, function (i, el) {
              combo.append("<option>" + el + "</option>");
          });

          if (selectedItem)
            combo.val(selectedItem);

          return combo;
      } // _getDropDownList

  }; // return

  function createPolygonFromBounds(latLngBounds) {

      latlngs = [];

      latlngs.push(latLngBounds.getSouthWest());//bottom left
      latlngs.push(latLngBounds.getSouthEast());//bottom right
      latlngs.push(latLngBounds.getNorthEast());//top right
      latlngs.push(latLngBounds.getNorthWest());//top left
      latlngs.push(latLngBounds.getSouthWest());//bottom left

     return new L.polygon(latlngs).toGeoJSON();

   } //createPolygonFromBounds

}); //ckan.module wms_view
