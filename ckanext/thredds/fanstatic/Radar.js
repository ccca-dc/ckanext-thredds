var RadarViewer = function(options) {
    NCWMSGridTimeseriesViewer.call(this, options);
};

RadarViewer.prototype = Object.create(NCWMSGridTimeseriesViewer.prototype);

RadarViewer.prototype.createMap = function(map) {
    NCWMSGridTimeseriesViewer.prototype.createMap.call(this, map);
    this.map.timeDimension.on('availabletimeschanged', (function() {        
        var times = this.map.timeDimension.getAvailableTimes();
        if (times.length){
            var last_time = times[times.length - 1];
            var now = new Date().getTime();
            // show message if last time available is more than two hours ago
            if ((now - last_time) / (1000 * 60 * 60) > 2){
                $("#map-warning").html("WARNING: Real-time data is temporarily unavailable. Please, try again later.");
                if ((now - last_time) / (1000 * 60 * 60) > 4){
                    $("#map-warning").html("WARNING: Real-time data is unavailable due to an extraordinary incident.<br/>We apologise for any inconvenience this may have caused you and we appreciate your understanding.");
                }
                $("#map-warning").show();
            }           
        }
    }).bind(this));
};

RadarViewer.prototype.addPositionMarker = function(point) {
    var circle = NCWMSGridTimeseriesViewer.prototype.addPositionMarker.call(this, point);
    if (point.data) {
        this._loadBuoyData(point, circle.options.fillColor);
    }
};

RadarViewer.prototype._loadBuoyData = function(point, color) {
    for (var i = 0, l = point.data.length; i < l; i++) {
        var variableSettings = point.data[i];
        if (variableSettings) {
            this._loadVariableData(point, variableSettings, i, color);
        }
    }
    this._addBuoyMarker(point);
};

RadarViewer.prototype._loadVariableData = function(point, settings, order, color) {
    var source = {
        url: 'facilities/mooring/requests/get_plotting_data.php',
        params: {
            id_platform: settings.platform,
            id_instrument: settings.instrument,
            id_variable: settings.variable,
            units: 'scientific'
        }
    };

    $.getJSON(source.url, source.params, (function(data) {
        point.data[order].data = data.dataList.timeDimensionData;
        this._plotBuoyData(data, point, order, color);
        // when velocity and direction are loaded,
        // get component variables of the velocity
        if (point.data[0].data && point.data[3].data){
            this._processComponentData(point, color);
        }
        // when direction is loaded, create serie of direction differences
        if (order == 3){
            this._plotDirectionDifferences('buoy', point.data[3].data);
        }
    }).bind(this));
};

RadarViewer.prototype._plotBuoyData = function(data, point, order, color) {
    var titleChart = data.displayName.replace(/CTD\d\-/, " at ") + ' (' + data.inputUnits + ')';
    titleChart = titleChart.replace(/(.*) ([\w])(-1)/, "$1/$2");
    var tooltipUnits = data.inputUnits;
    tooltipUnits = tooltipUnits.replace(/(.*) ([\w])(-1)/, "$1/$2");

    var layer = this.layers[order];
    if (!layer.chart) {
        setTimeout((function(data, point, order, color) {
            this._plotBuoyData(data, point, order, color);
        }).bind(this, data, point, order, color), 500);
        return;
        // layer.chart = this.createChart(layer);
    }
    var serieName = layer.name + ' from ' + point.platformName;
    if (point.sourceLegend){
        serieName = point.sourceLegend;
    }
    var serie = {
        name: serieName,
        type: 'line',
        dashStyle: 'shortdot',
        id: Math.random().toString(36).substring(7),
        color: color,
        data: this._convertData(data.dataList.timeDimensionData, data.inputUnits),        
        tooltip: {
            valueDecimals: 2,
            valueSuffix: ' ' + this._convertInputUnits(data.inputUnits),
            xDateFormat: '%A, %b %e, %H:%M',
        },
    };
    layer.chart.addSeries(serie);
};

RadarViewer.prototype._convertData = function(data, units) {
    if (units == 'cm s-1') {
        data = _.map(data, function(value) {
            if (!value[1]){
                return [value[0], null];
            }
            return [value[0], value[1] / 100];
        });
    }
    return data;
}

RadarViewer.prototype._convertInputUnits = function(units) {
    if (units == 'cm s-1') {
        units = 'm/s';
    }
    return units;
}

RadarViewer.prototype._addBuoyMarker = function(point) {
    var iconOptions = {
        iconUrl: 'facilities/mooring/images/buoy.png',
        iconSize: [25, 30],
        popupAnchor: [-3, -5],
        iconAnchor: [12, 37],
        labelAnchor: [5, -20]
    };
    var iconBuoy = new L.icon(iconOptions);
    var markerOptions = {
        icon: iconBuoy,
        title: point.platformName
    };

    var marker = L.marker(point.position, markerOptions).bindLabel(point.platformName, {
        noHide: false,
        direction: 'right'
    }).addTo(this.map);

};

RadarViewer.prototype._processComponentData = function(point, color){
    // Eastward sea water velocity
    var velocity = point.data[0].data;
    var direction = _.unzip(point.data[3].data);

    var components = _.map(velocity, function(value) {
        if (!value[1]){
            return [[value[0], null], [value[0], null]];
        }
        var vel = value[1] / 100;
        var dirIndex = _.indexOf(direction[0], value[0], true);
        if (dirIndex > -1){
            if (!direction[1][dirIndex]){
                return [[value[0], null], [value[0], null]];
            }
            var dir = direction[1][dirIndex];
            dir = dir * (Math.PI/180);
            return [[value[0], vel*Math.sin(dir)], [value[0], vel*Math.cos(dir)]];
        }
        return [[value[0], null], [value[0], null]];
    });

    components = _.unzip(components);

    var data = {
        'displayName': 'Eastward sea water velocity',
        'inputUnits': 'm/s',
        'dataList': {
            'timeDimensionData': components[0]
        }
    };
    this._plotBuoyData(data, point, 1, color);
    data = {
        'displayName': 'Northward sea water velocity',
        'inputUnits': 'm/s',
        'dataList': {
            'timeDimensionData': components[1]
        }
    };
    this._plotBuoyData(data, point, 2, color);
};

RadarViewer.prototype.loadData = function(layer, point, callback) {
    var color = this.colors[this.currentColor % this.colors.length];
    var newCallback = function(layer, point, color, callback, data){        
        if (layer.params.layers == 'WSPE_DIR'){
            this._plotDirectionDifferences('radar', data);
        }
        if (callback !== undefined) {
            callback(data);
        }        
    }
    NCWMSGridTimeseriesViewer.prototype.loadData.call(this, layer, point, newCallback.bind(this, layer, point, color, callback));
};

RadarViewer.prototype._plotDirectionDifferences = function(source, data){
    if (!this._differencesData){
        this._differencesData = {};
    }
    if (this._differencesData.hasOwnProperty(source)) {
        // TODO: we could receive more data from radar, but not always from the 
        // buoy point. We have to reject data of other points and accept HF radar data for the buoy point
        return;
    }
    this._differencesData[source] = data;
    if (!this._differencesData.hasOwnProperty('radar') || !this._differencesData.hasOwnProperty('buoy')){
        return;
    }

    var fakeLayer = {
        name: "Direction differences between HF Radar and buoy",
        units: 'degrees',
        params: {
            layers: "WSPE_DIR_DIFF",
        },
    };
    var chart = this.createChart(fakeLayer);

    var radar = this._differencesData['radar'];
    var buoy = this._differencesData['buoy'];

    var differences = _.map(buoy, function(buoyValue) {
        if (!buoyValue[1]){
            return [buoyValue[0], null];
        }
        var time = new Date(buoyValue[0]).toISOString();
        var radIndex = _.indexOf(radar.time, time, true);
        if (radIndex < 0){
            return [buoyValue[0], null];
        }

        if (!radar.values[radIndex]){
            return [buoyValue[0], null];
        }
        var diff = radar.values[radIndex] - buoyValue[1];
        if (diff > 180){
            diff = 360 - diff;
        }
        if (diff < -180){
            diff = 360 + diff;
        }        
        return [buoyValue[0], diff];
    });    

    var serie = {
        name: 'Direction of sea water velocity differences (HF Radar - Buoy)',
        type: 'line',
        id: Math.random().toString(36).substring(7),
        data: differences,
        tooltip: {
            valueDecimals: 2,
            valueSuffix: ' degrees',
            xDateFormat: '%A, %b %e, %H:%M',
            headerFormat: '<span style="font-size: 12px; font-weight:bold;">{point.key} (Click to visualize the map on this time)</span><br/>'
        }
    };
    chart.addSeries(serie);

};

Radar = {
    PATH: "facilities/radar/",

    BASE_MEDIA_PATH: 'files/images_iconos/',

    Map: {
        init: function() {

            var endDate = new Date();
            if (endDate.getUTCMinutes() > 30) {
                endDate.setUTCHours(endDate.getUTCHours() - 1);
            } else {
                endDate.setUTCHours(endDate.getUTCHours() - 2);
            }
            endDate.setUTCMinutes(0, 0, 0);

            var wms_server = 'http://thredds.socib.es/thredds/wms/observational/hf_radar/hf_radar_ibiza-scb_codarssproc001_L1_agg/hf_radar_ibiza-scb_codarssproc001_L1_agg_best.ncd';
            var options = {
                container: 'map',
                updateTimeDimension: true,
                sourceLegend: 'HF radar (0.9 m)',
                layers: [{
                    name: "Sea Water Velocity",
                    url: wms_server,
                    params: {
                        layers: "sea_water_velocity",
                        styles: 'prettyvec/rainbow',
                        markerscale: 17,
                        colorscalerange: "0, 0.4",
                        abovemaxcolor: "extend",
                        belowmincolor: "extend",
                        zIndex: 100,
                        attribution: "SOCIB HF RADAR (<a href='http://thredds.socib.es/thredds/catalog/observational/hf_radar/hf_radar_ibiza-scb_codarssproc001_L1_agg/catalog.html'>access to data</a>)"
                    },
                    visible: true,
                    singleTile: true,
                    autoExtent: false,
                    timeseriesWhenNotVisible: true,
                }, {
                    name: "Eastward sea water velocity",
                    url: wms_server,
                    params: {
                        layers: "U",
                        styles: 'boxfill/rainbow',
                        abovemaxcolor: "extend",
                        belowmincolor: "extend",
                        colorscalerange: "-0.4, 0.4",
                        opacity: 0.7,
                        zIndex: 90,
                    },
                    visible: false,
                    singleTile: true,
                    autoExtent: false,
                    timeseriesWhenNotVisible: true,
                }, {
                    name: "Northward sea water velocity",
                    url: wms_server,
                    params: {
                        layers: "V",
                        styles: 'boxfill/rainbow',
                        colorscalerange: "-0.4, 0.4",
                        abovemaxcolor: "extend",
                        belowmincolor: "extend",
                        opacity: 0.7,
                        zIndex: 90,
                    },
                    visible: false,
                    singleTile: true,
                    autoExtent: false,
                    timeseriesWhenNotVisible: true,
                }, {
                    name: "Direction of sea water velocity",
                    url: wms_server,
                    params: {
                        layers: "WSPE_DIR",
                        styles: 'boxfill/rainbow',
                        colorscalerange: "0, 360",
                        opacity: 0.7,
                        zIndex: 90,
                    },
                    visible: false,
                    singleTile: true,
                    autoExtent: false,
                    timeseriesWhenNotVisible: true,
                }, {
                    name: "Quality flag",
                    url: wms_server,
                    params: {
                        layers: "QC_WSPE_DIR",
                        styles: 'boxfill/rainbow',
                        colorscalerange: "0, 9",
                        opacity: 0.3,
                        numcolorbands: 10,
                        zIndex: 80,
                    },
                    visible: false,
                    singleTile: true,
                    autoExtent: false,
                }],
                mapOptions: {
                    zoom: 10,
                    center: [38.705, 1.15],
                    fullscreenControl: true,
                    timeDimensionOptions: {
                        timeInterval: "P3M/" + endDate.toISOString(),
                        period: "PT1H",
                        currentTime: endDate.getTime()
                    },
                    timeDimensionControlOptions: {
                        autoPlay: false,
                        playerOptions: {
                            transitionTime: 500,
                            loop: true,
                        }
                    }
                },
                proxy: Radar.PATH + 'request/threddsProxy.php',
                default_range_selector: 1,
                default_markers: [{
                    name: ' ',
                    platformName: 'Buoy at Ibiza Channel',
                    sourceLegend: 'Buoy (1.5 m)',
                    position: [38.82445, 0.783667],
                    data: [{
                        platform: 146,
                        instrument: 522,
                        variable: 90207 // CUR_SPE
                    }, null, null, {
                        platform: 146,
                        instrument: 522,
                        variable: 90206 // CUR_DIR
                    }],

                }]
            };

            this.gridViewer = new RadarViewer(options);

            this.map = this.gridViewer.getMap();

            this.map.on('popupopen', (function(e) {
                var popup = e.popup;
                popup.setContent(this.get_popup_content(popup.station));
            }).bind(this));

            var stations = [{
                name: 'Puig des Galfí',
                lat: 38.9519,
                lon: 1.21915,
                code: 'GALF',
                model: 'CODAR SeaSonde',
                location: 'Western coast of Ibiza (Puig des Galfí)',
                frequency: '13.5 MHz',
                bandwidth: '90 KHz',
                antenna_pattern: 'Measured',
                photo: 'facilities/radar/images/radar-galf.jpg'
            }, {
                name: 'Formentera',
                lat: 38.6662333,
                lon: 1.3887500,
                code: 'FORM',
                model: 'CODAR SeaSonde',
                location: 'Western coast of Formentera',
                frequency: '13.5 MHz',
                bandwidth: '90 KHz',
                antenna_pattern: 'Measured',
                photo: 'facilities/radar/images/radar-form.jpg'
            }];

            $.each(stations, (function(i, station) {
                if (!station.marker)
                    station.marker = this.place_station_marker(station);
            }).bind(this));
        },

        place_station_marker: function(station) {
            var iconOptions = {
                iconUrl: 'files/images_iconos/radar_map.png',
                iconSize: [30, 30],
                popupAnchor: [-3, -5],
                iconAnchor: [10, 10],
                labelAnchor: [6, 0]
            };
            var markerOptions = {
                icon: new L.icon(iconOptions),
                title: station.name
            };

            var labelDirection = 'right';
            var label = station.name;
            var marker = L.marker([station.lat, station.lon], markerOptions).bindLabel(label, {
                noHide: true,
                direction: labelDirection
            }).addTo(this.map).showLabel();

            marker.bindPopup('');
            marker._popup.station = station;

            return marker;
        },

        get_popup_content: function(station) {
            var html = '<div class="radar-station">';
            html += '<img src="' + station.photo + '" title="Station image" />';
            html += '<ul><li><span class="station-attribute">Name:</span> ' + station.code + "</li>";
            html += '<li><span class="station-attribute">Model:</span> ' + station.model + "</li>";
            html += '<li><span class="station-attribute">Location:</span> ' + station.location + "</li>";
            html += '<li><span class="station-attribute">LON:</span> ' + this.decimalDegrees2DMS(station.lon, 'Longitude') + "</li>";
            html += '<li><span class="station-attribute">LAT:</span> ' + this.decimalDegrees2DMS(station.lat, 'Latitude') + "</li>";
            html += '<li><span class="station-attribute">Center Frequency:</span> ' + station.frequency + "</li>";
            html += '<li><span class="station-attribute">Bandwidth:</span> ' + station.bandwidth + "</li>";
            html += '<li><span class="station-attribute">Antenna pattern:</span> ' + station.antenna_pattern + "</li></ul>";
            html += '</div>';
            return html;
        },

        /*
            Converts a Decimal Degree Value into
            Degrees Minute Seconds Notation.

            Pass value as double
            type = {Latitude or Longitude} as string

            returns a string as D:M:S:Direction
        */
        decimalDegrees2DMS: function(value, type) {
            degrees = Math.floor(value);
            minutes = Math.abs((value - degrees) * 60).toFixed(2);
            // subseconds = Math.abs((submin-minutes) * 60);
            direction = "";
            if (type == "Longitude") {
                if (value < 0)
                    direction = "W";
                else if (value > 0)
                    direction = "E";
                else
                    direction = "";
            } else if (type == "Latitude") {
                if (value < 0)
                    direction = "S";
                else if (value > 0)
                    direction = "N";
                else
                    direction = "";
            }
            degrees = Math.abs(degrees);
            notation = degrees + "° " + minutes + "' " + direction;
            return notation;
        }

    },

    Reports: {
        availableMonths: [],
        form: null,

        init: function() {
            this.availableMonths = [];
            this.getCurrentReports();
        },

        getCurrentReports: function(){
            $.getJSON(Radar.PATH + 'request/monthlyReports.php',
                      this.processCurrentReports.bind(this));
        },

        processCurrentReports: function(data){
            for (var i=0, l=data.length; i<l; i++){
                this.availableMonths.push(data[i].month);
            }
            this.initForm();
        },

        initForm: function(){
            this.form = $("#reports").find('form');
            var yearSelect = this.form.find('select[name="year"]');
            var years = [];            
            for (var i=0, l=this.availableMonths.length; i<l; i++){
                var year = this.availableMonths[i].substr(0, 4);
                if (years.indexOf(year) < 0){
                    years.push(year);
                    yearSelect
                        .append($('<option>', { value : year })
                        .text(year));
                }
            }
            yearSelect.change(this.changeYear.bind(this));
            yearSelect.val(years[years.length - 1]);
            this.changeYear();
            this.form.submit(this.downloadReport.bind(this));
        },

        changeYear: function(){
            var yearSelect = this.form.find('select[name="year"]');
            var currentYear = yearSelect.val();

            var monthSelect = this.form.find('select[name="month"]');
            monthSelect.find('option').remove();
            var months = [];
            for (var i=0, l=this.availableMonths.length; i<l; i++){
                var year = this.availableMonths[i].substr(0, 4);
                if (currentYear == year){
                    var month = this.availableMonths[i].substr(4, 2);
                    if (months.indexOf(month) < 0){
                        months.push(month);
                        monthSelect
                            .append($('<option>', { value : month })
                            .text(month));
                    }
                }
            }
        },

        downloadReport: function(e){
            e.stopPropagation();

            var yearSelect = this.form.find('select[name="year"]');
            var currentYear = yearSelect.val();
            var monthSelect = this.form.find('select[name="month"]');            
            var currentMonth = monthSelect.val();

            var url = "/files/reports/HF_Radar/SOCIB_HFRadar_Report";
            url += currentYear;
            url += currentMonth;
            url += ".pdf";

            this.form.attr("target", "_blank");
            this.form.attr("method", "post");
            this.form.attr("action", url);
            return;
        }
    },


};