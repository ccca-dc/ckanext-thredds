ckan.module('wms_view', function ($) {
  return {
      /* options object can be extended using data-module-* attributes */
      options: {
          resource_id:''
      },

      initialize: function () {
        $.proxyAll(this, /_on/);
        var options = this.options;

        var startDate = new Date();
        startDate.setUTCHours(0, 0, 0, 0);

        var map = L.map('map', {
            zoom: 7,
            fullscreenControl: true,
            timeDimensionControl: true,
            timeDimensionControlOptions: {
                position: 'bottomleft',
                playerOptions: {
                    transitionTime: 1000,
                }
            },
            timeDimension: true,
            center: [47.3, 13.9]
        });

        this.sandbox = ckan.sandbox();
        // ckan.sandbox('GET','thredds_get_layers','?id=decaacbb-3979-4b14-9b7a-abaee64bc983', function(json) {console.log(json)},function(json) {console.log(json)});
        this.sandbox.client.call('GET','thredds_get_layers',
                                 '?id='+ this.options.resource_id,
                                 this._onHandleData,
                                 function(json) {console.log(json);}
                                ),

        var cccaWMS = "https://sandboxdc.ccca.ac.at/wms_proxy/" + this.options.resource_id;

        var cccaHeightLayer = L.tileLayer.wms(cccaWMS, {
            layers: window.wmslayer,
            format: 'image/png',
            transparent: true,
            colorscalerange: '-20,20',
            abovemaxcolor: "extend",
            belowmincolor: "extend",
            numcolorbands: 100,
            styles: 'boxfill/rainbow'
        });

        var markers = [{
            name: 'Vienna',
            position: [48.210033, 16.363449]
        }, {
            name: 'Graz',
            position: [47.076668, 15.421371]
        }, {
            name: 'Salzburg',
            position: [47.811195, 13.033229]
        }, {
            name: 'Innsbruck',
            position: [47.259659, 11.400375]
        }];

        //var proxy = '/wms_proxy';
        var cccaHeightTimeLayer = L.timeDimension.layer.wms.timeseries(cccaHeightLayer, {
            //proxy: proxy,
            updateTimeDimension: true,
            markers: markers,
            name: "Surface Air Temperature",
            units: "Celsius",
            enableNewMarkers: true
        });


        var cccaLegend = L.control({
            position: 'bottomright'
        });
        cccaLegend.onAdd = function(map) {
            var src = cccaWMS + "?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetLegendGraphic&LAYER=tas&colorscalerange=-20,20&PALETTE=rainbow&numcolorbands=100&transparent=FALSE";
            var div = L.DomUtil.create('div', 'info legend');
            div.innerHTML +=
                '<img src="' + src + '" alt="legend">';
            return div;
        };


        var overlayMaps = {
            "Surface Air Temperature": cccaHeightTimeLayer
        };

        map.on('overlayadd', function(eventLayer) {
            if (eventLayer.name == 'Surface Air Temperature') {
                cccaLegend.addTo(this);
            }
        });

        map.on('overlayremove', function(eventLayer) {
            if (eventLayer.name == 'Surface Air Temperature') {
                map.removeControl(cccaLegend);
            }
        });

        var baseLayers = getCommonBaseLayers(map); // see baselayers.js
        L.control.layers(baseLayers, overlayMaps).addTo(map);

        cccaHeightTimeLayer.addTo(map);

    },

    _onHandleData: function(json) {
        if (json.success) {
            $.map(json.result, function( value, key ) {
                window.wmslayer = key.toString(); }
                 );

        }
    }

  };
});
