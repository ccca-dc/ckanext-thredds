ckan.module('wms_view', function ($) {
  return {
    initialize: function () {
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

        //var sapoWMS = "http://thredds.socib.es/thredds/wms/operational_models/oceanographical/wave/model_run_aggregation/sapo_ib/sapo_ib_best.ncd";
        //var sapoWMS = "http://localhost:8080/thredds/wms/testAll/tx_QuantileMapped_MPI-M-MPI-ESM-LR_rcp85_r1i1p1_SMHI-RCA4_v1_day_19700101-19701231.nc";
        var sapoWMS = "http://localhost:8080/thredds/wms/ckanAll/resources/dec/aac/bb-3979-4b14-9b7a-abaee64bc983"
        //var sapoWMS = "http://localhost:8080/thredds/wms/ckanAll/resources/ed6/e87/6f-1fb4-4952-86b1-0872b23d6029"
        //var sapoWMS = "http://localhost:8080/thredds/wms/testAll/tx_QuantileMapped_MPI-M-MPI-ESM-LR_rcp85_r1i1p1_SMHI-RCA4_v1_day_19700101-19701231.nc"
        //var sapoWMS = "http://localhost:8080/thredds/wms/ckanAll/resources/382/306/62-6f7a-4519-b70a-8d125923070a"
        //var sapoWMS = "http://localhost:8080/thredds/wms/ckanAll/resources/66c/8cd/07-737a-4cdb-9a6d-05f4dc779ca4"
        //var sapoWMS = "http://localhost:8080/thredds/wms/ckanAll/resources/0cb/7c3/96-b232-469a-85c4-138bd2868506?service=WMS&version=1.3.0&request=GetCapabilities"
        var sapoHeightLayer = L.tileLayer.wms(sapoWMS, {
            layers: 'tas',
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

        var proxy = '/wms_proxy';
        var sapoHeightTimeLayer = L.timeDimension.layer.wms.timeseries(sapoHeightLayer, {
            proxy: proxy,
            updateTimeDimension: true,
            markers: markers,
            name: "Surface Air Temperature",
            units: "Celsius",
            enableNewMarkers: true
        });


        var sapoLegend = L.control({
            position: 'bottomright'
        });
        sapoLegend.onAdd = function(map) {
            var src = sapoWMS + "?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetLegendGraphic&LAYER=tas&colorscalerange=-20,20&PALETTE=rainbow&numcolorbands=100&transparent=FALSE";
            var div = L.DomUtil.create('div', 'info legend');
            div.innerHTML +=
                '<img src="' + src + '" alt="legend">';
            return div;
        };


        var overlayMaps = {
            "Surface Air Temperature": sapoHeightTimeLayer
        };

        map.on('overlayadd', function(eventLayer) {
            if (eventLayer.name == 'Surface Air Temperature') {
                sapoLegend.addTo(this);
            }
        });

        map.on('overlayremove', function(eventLayer) {
            if (eventLayer.name == 'Surface Air Temperature') {
                map.removeControl(sapoLegend);
            }
        });

        var baseLayers = getCommonBaseLayers(map); // see baselayers.js
        L.control.layers(baseLayers, overlayMaps).addTo(map);

        sapoHeightTimeLayer.addTo(map);

    }
  };
});
