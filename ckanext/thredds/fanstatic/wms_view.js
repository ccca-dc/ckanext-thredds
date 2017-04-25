ckan.module('wms_view', function ($) {
  return {
      /* options object can be extended using data-module-* attributes */
      options: {
          resource_id:'',
          site_url:''
      },

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

      },

      initializePreview: function () {
        var startDate = new Date();
        startDate.setUTCHours(0, 0, 0, 0);

        var self = this;
        var wmslayers = $.map(self.options.layers, function( value, key ) { return value.children});
        var wmsabstracts = $.map(self.options.layers, function( value, key ) { return value.label } );

        var palette_selection = self.options.layers_details.defaultPalette;
        var style_selection = self.options.layers_details.supportedStyles[0];

        var min_value = self.options.layers_details.scaleRange[0];
        var max_value = self.options.layers_details.scaleRange[1];

        var opacity = 1;

        var map = L.map('map', {
            zoom: 7,
            fullscreenControl: true,
            timeDimensionControl: true,
            timeDimensionControlOptions: {
                position: 'bottomleft',
                playerOptions: {
                    transitionTime: 1000,
                },
                minSpeed: 0.1,
                maxSpeed: 2.0
            },
            timeDimension: true,
            center: [47.3, 13.9]
        });

        // ------------------------------------------------
        // Create control elements for first layer
        // Style
        $( "#style" ).append( 
          this._getDropDownList(
            'styles','select-styles',self.options.layers_details.supportedStyles) 
        );

        // Palette
        $( "#palette" ).append( 
          this._getDropDownList(
            'palettes','select-palettes',self.options.layers_details.palettes) 
        );

        // Minimum/Maximum
        $( "#min-field" ).append( 
          $("<input id='min-value' type='text' class='numbersOnly' value=" + self.options.layers_details.scaleRange[0].toString() + ">")
        );

        $( "#max-field" ).append( 
          $("<input id='max-value' type='text' class='numbersOnly' value=" + self.options.layers_details.scaleRange[1].toString() + ">")
        );

        // Opacity
        $( "#opacity" ).append( 
          $("<input id='opacity-value' type='range' min='0' max='1' step='0.1' value=" + opacity.toString() + " />")
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

        $('#opacity-value').on('change', function() {
          opacity = this.value;
          // Update Preview
          cccaHeightTimeLayer.setOpacity(opacity);
 
        });

        var cccaWMS = self.options.site_url + "tds_proxy/wms/" + self.options.resource_id;

        var cccaHeightLayer = L.tileLayer.wms(cccaWMS, {
            layers: wmslayers[0].id,
            format: 'image/png',
            transparent: true,
            colorscalerange: min_value + ',' + max_value,
            abovemaxcolor: "extend",
            belowmincolor: "extend",
            numcolorbands: 100,
            styles: style_selection + '/' + palette_selection
        });

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

        var cccaHeightTimeLayer = L.timeDimension.layer.wms.timeseries(cccaHeightLayer, {
            updateTimeDimension: true,
            markers: markers,
            name: wmsabstracts[0],
            legendname: wmslayers[0].label,
            //maxValues: 4000,
            units: self.options.layers_details.units,
            enableNewMarkers: true
        });

        var cccaLegend = L.control({
            position: 'bottomright'
        });
        cccaLegend.onAdd = function(map) {
            var src = cccaWMS + "?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetLegendGraphic&LAYER=" + wmslayers[0].id + "&colorscalerange="+ min_value + ',' + max_value + "&PALETTE="+ palette_selection +"&numcolorbands=100&transparent=TRUE";
            var div = L.DomUtil.create('div', 'info legend');
            div.innerHTML +=
                '<img src="' + src + '" alt="legend">';
            return div;
        };


        var overlayMaps = {};
        overlayMaps[wmsabstracts[0].toString()] = cccaHeightTimeLayer;

        map.on('overlayadd', function(eventLayer) {
            if (eventLayer.name == wmsabstracts[0]) {
                cccaLegend.addTo(this);
            }
        });

        map.on('overlayremove', function(eventLayer) {
            if (eventLayer.name == wmsabstracts[0]) {
                map.removeControl(cccaLegend);
            }
        });

        var baseLayers = getCommonBaseLayers(map); // see baselayers.js
        L.control.layers(baseLayers, overlayMaps).addTo(map);

        cccaHeightTimeLayer.addTo(map);
      },


      _onHandleDataDetails: function(json) {
        if (json.success) {
          self.options.layers_details = json.result;
          this.initializePreview();
        }
      },

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
        }
      },

      _onHandleError: function(error) {
        alert("Please login to use this view");
        throw new Error("Something went badly wrong!");
      },

      _getDropDownList: function(name, id, optionList) {
          var combo = $("<select></select>").attr("id", id).attr("name", name);
      
          $.each(optionList, function (i, el) {
              combo.append("<option>" + el + "</option>");
          });
      
          return combo;
      }
      
  };
});
