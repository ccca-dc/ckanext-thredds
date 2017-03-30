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

        var startDate = new Date();
        startDate.setUTCHours(0, 0, 0, 0);

      },

      showPreview: function (wmsInfo) {
        var self = this;
        var wmslayers = $.map(wmsInfo, function( value, key ) { return key.toString(); } );

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


        var cccaWMS = self.options.site_url + "/wms_proxy/" + self.options.resource_id;

        var cccaHeightLayer = L.tileLayer.wms(cccaWMS, {
            layers: wmslayers[0],
            format: 'image/png',
            transparent: true,
            colorscalerange: '-20,20',
            abovemaxcolor: "extend",
            belowmincolor: "extend",
            numcolorbands: 100,
            styles: 'boxfill/rainbow'
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
            units: "Celsius",
            enableNewMarkers: true
        });


        var cccaLegend = L.control({
            position: 'bottomright'
        });
        cccaLegend.onAdd = function(map) {
            var src = cccaWMS + "?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetLegendGraphic&LAYER=" + wmslayers[0] + "&colorscalerange=-20,20&PALETTE=rainbow&numcolorbands=100&transparent=FALSE";
            var div = L.DomUtil.create('div', 'info legend');
            div.innerHTML +=
                '<img src="' + src + '" alt="legend">';
            return div;
        };


        var overlayMaps = {
            [wmsabstracts[0]]: cccaHeightTimeLayer
        };

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

    _onHandleData: function(json) {
        if (json.success) {
            this.showPreview(json.result);
        }
    },

		_onHandleError: function(error) {
        console.log(error);
		}

  };
});
