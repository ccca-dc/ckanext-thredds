var NCWMSGridTimeseriesViewer = function(options) {
    this.container = options.container || 'map';
    this.layers = options.layers;
    this.baseMaps = options.baseMaps;
    this._defaultMarkers = options.default_markers || [];
    this._sourceLegend = options.sourceLegend || null;
    if (options.updateTimeDimension === undefined){
        this._updateTimeDimension = true;        
    } else {
        this._updateTimeDimension = options.updateTimeDimension;        

    }
    this.mapOptions = options.mapOptions || {};
    if (options.default_range_selector === undefined) {
        this.default_range_selector = 1;
    } else {
        this.default_range_selector = options.default_range_selector;
    }
    this.proxy = options.proxy || null;
    this.colors = options.colors || ["#2f7ed8", "#0d233a", "#8bbc21", "#910000",  "#492970", "#f28f43", "#77a1e5", "#c42525", "#a6c96a"];
    this.currentColor = 0;
    this.createMap(options.map);
    this.pendingLayers = 0;
    for (var i = 0, l = this.layers.length; i < l; i++) {
        var layer = this.layers[i];
        if (layer.params.colorscalerange && layer.params.colorscalerange == 'auto') {
            this.pendingLayers++;
            this.getLayerMinMax(layer, this.addLayersToMap.bind(this));
        }
    }
    this.addLayersToMap();

};

NCWMSGridTimeseriesViewer.prototype.addLayersToMap = function() {
    if (this.pendingLayers > 0)
        return;
    if (this.map) {
        for (var i = 0, l = this.layers.length; i < l; i++) {
            var layer = this.layers[i];
            var wms_options = {
                format: 'image/png',
                transparent: true,
            };
            for (var attribute in layer.params) {
                wms_options[attribute] = layer.params[attribute];
            }
            if (layer.singleTile) {
                layer.tilelayer = L.nonTiledLayer.wms(layer.url, wms_options);
            } else {
                layer.tilelayer = L.tileLayer.wms(layer.url, wms_options);
            }

            layer.timeLayer = L.timeDimension.layer.wms(layer.tilelayer, {
                proxy: this.proxy,
                updateTimeDimension: (i == 0) && this._updateTimeDimension
            });

            this.layerControl.addOverlay(layer.timeLayer, layer.name);
            if (layer.legend === undefined || layer.legend) {
                var variableLegend = L.control({
                    position: 'bottomright'
                });
                variableLegend.onAdd = this.addLegend.bind(this, layer);

                variableLegend.onRemove = this.removeLegend.bind(this, layer);
                layer.timeLayer.legend = variableLegend;
            }
            if (layer.visible) {
                layer.timeLayer.addTo(this.map);
            }
            if (layer.visible || layer.timeseriesWhenNotVisible) {
                if (layer.timeseries === undefined || layer.timeseries) {
                    this.createChartContainer(layer);
                }
            }
        }
    }
};

NCWMSGridTimeseriesViewer.prototype.addDefaultMarkers = function() {
    for (var i = 0, l = this._defaultMarkers.length; i < l; i++) {
        this.addPositionMarker(this._defaultMarkers[i]);
    }

};

NCWMSGridTimeseriesViewer.prototype.addPositionMarker = function(point) {
    var color = this.getNextColor();
    var circle = L.circleMarker([point.position[0], point.position[1]], {
        color: '#FFFFFF',
        fillColor: color,
        fillOpacity: 0.8,
        radius: 5,
        weight: 2
    }).addTo(this.map);
    var afterLoadData = function(layer, color, count, data) {
        var serie = this.showData(layer, color, data, point.name);
        if (count == 0) {
            L.timeDimension.layer.circleLabelMarker(circle, {
                serieId: serie,
                dataLayer: layer,
                proxy: this.proxy
            }).addTo(this.map);
        }
        layer.chart.hideLoading();
        // icon.html(data.values[1]); // TODO.
    };

    for (var i = 0, l = this.layers.length; i < l; i++) {
        var layer = this.layers[i];
        if (layer.timeseries !== undefined && !layer.timeseries) {
            continue;
        }
        if (layer.timeseriesWhenNotVisible || (layer.timeLayer && this.map.hasLayer(layer.timeLayer))) {
            if (layer.chart)
                layer.chart.showLoading();
            this.loadData(layer, circle._point, afterLoadData.bind(this, layer, color, i));
        }
    }
    return circle;
};


NCWMSGridTimeseriesViewer.prototype.getLayerMinMax = function(layer, callback) {
    var url = layer.url + '?service=WMS&version=1.1.1&request=GetMetadata&item=minmax';
    url = url + '&layers=' + layer.params.layers;
    url = url + '&srs=EPSG:4326';
    var size = this.map.getSize();
    url = url + '&BBox=' + this.map.getBounds().toBBoxString();
    url = url + '&height=' + size.y;
    url = url + '&width=' + size.x;

    if (this.proxy) url = this.proxy + '?url=' + encodeURIComponent(url);
    $.getJSON(url, (function(layer, data) {
        var range = data.max - data.min;

        var min = Math.floor(data.min);
        var max = Math.floor(data.max + 2);
        layer.params.colorscalerange = min + "," + max;
        this.pendingLayers--;
        if (callback !== undefined) {
            callback();
        }
    }).bind(this, layer));
};

NCWMSGridTimeseriesViewer.prototype.getNextColor = function() {
    return this.colors[this.currentColor++ % this.colors.length];
};

NCWMSGridTimeseriesViewer.prototype.getMap = function() {
    return this.map;
};

NCWMSGridTimeseriesViewer.prototype.showData = function(layer, color, data, positionName) {
    var position = data.latitude + ', ' + data.longitude;
    if (positionName !== undefined) {
        position = positionName;
    }
    return this.addSerie(layer, data.time, data.values, position, data.url, color);
};

NCWMSGridTimeseriesViewer.prototype.loadData = function(layer, point, callback) {
    if (layer.date_range === undefined || layer.date_range === null) {
        this.loadDateRange(layer, (function(layer) {
            this.loadData_(layer, point, callback);
        }).bind(this, layer));
    } else {
        this.loadData_(layer, point, callback);
    }
};

NCWMSGridTimeseriesViewer.prototype.loadData_ = function(layer, point, callback) {
    var min = new Date(layer.timeLayer._getNearestTime(layer.date_range.min.getTime()));
    var max = new Date(layer.timeLayer._getNearestTime(layer.date_range.max.getTime()));

    var url = layer.url + '?SERVICE=WMS&VERSION=1.1.1&REQUEST=GetFeatureInfo&SRS=EPSG:4326';
    url = url + '&LAYER=' + layer.params.layers;
    url = url + '&QUERY_LAYERS=' + layer.params.layers;
    url = url + '&X=' + point.x + '&Y=' + point.y + '&I=' + point.x + '&J=' + point.y;
    var size = this.map.getSize();
    url = url + '&BBox=' + this.map.getBounds().toBBoxString();
    url = url + '&WIDTH=' + size.x + '&HEIGHT=' + size.y;
    url = url + '&INFO_FORMAT=text/xml';
    var url_without_time = url;
    url = url + '&TIME=' + min.toISOString() + '/' + max.toISOString();

    if (this.proxy) url = this.proxy + '?url=' + encodeURIComponent(url);

    $.get(url, (function(layer, data) {
        var result = {
            time: [],
            values: []
        };

        // Add min and max values to be able to get more data later
        if (layer.date_range.min > layer.minmaxdate_range.min) {
            result.time.push(layer.minmaxdate_range.min);
            result.values.push(null);
        }

        $(data).find('FeatureInfo').each(function() {
            var this_time = $(this).find('time').text();
            var this_data = $(this).find('value').text();
            try {
                this_data = parseFloat(this_data);
            } catch (e) {
                this_data = null;
            }
            result.time.push(this_time);
            result.values.push(this_data);
        });

        if (layer.date_range.max < layer.minmaxdate_range.max) {
            result.time.push(layer.minmaxdate_range.max);
            result.values.push(null);
        }

        result.longitude = $(data).find('longitude').text();
        try {
            result.longitude = parseFloat(result.longitude).toFixed(4);
        } catch (e) {}
        result.latitude = $(data).find('latitude').text();
        try {
            result.latitude = parseFloat(result.latitude).toFixed(4);
        } catch (e) {}
        result.url = url_without_time;

        if (callback !== undefined) {
            callback(result);
        }
    }).bind(this, layer));
};


NCWMSGridTimeseriesViewer.prototype._loadMoreData = function(layer, url, mindate, maxdate, callback) {
    var min = new Date(layer.timeLayer._getNearestTime(mindate.getTime()));
    var max = new Date(layer.timeLayer._getNearestTime(maxdate.getTime()));

    url = url + '&TIME=' + min.toISOString() + '/' + max.toISOString();

    if (this.proxy) url = this.proxy + '?url=' + encodeURIComponent(url);

    $.get(url, (function(data) {
        var result = {
            time: [],
            values: []
        };

        $(data).find('FeatureInfo').each(function() {
            var this_time = $(this).find('time').text();
            var this_data = $(this).find('value').text();
            try {
                this_data = parseFloat(this_data);
            } catch (e) {
                this_data = null;
            }
            result.time.push(this_time);
            result.values.push(this_data);
        });

        if (callback !== undefined) {
            callback(result);
        }
    }).bind(this)).fail(function() {
        if (callback !== undefined) {
            callback();
        }
    });
};

NCWMSGridTimeseriesViewer.prototype.loadDateRange = function(layer, callback) {
    var url = layer.url + '?service=WMS&version=1.1.1&request=GetMetadata&item=layerDetails';
    url = url + '&layerName=' + layer.params.layers;
    if (this.proxy) url = this.proxy + '?url=' + encodeURIComponent(url);
    $.getJSON(url, (function(layer, data) {
        layer.datesWithData = data.datesWithData;
        layer.minmaxdate_range = this.calculateMinMaxDate_(layer);
        var max = layer.minmaxdate_range.max;
        // check if max is a valid date
        if (!max.getTime || isNaN(max.getTime())) {
            return;
        }
        var min = new Date(Date.UTC(max.getUTCFullYear(), max.getUTCMonth(), max.getUTCDate()));

        if (this.default_range_selector === 0) {
            min.setUTCDate(min.getUTCDate() - 3);
        } else if (this.default_range_selector === 1) {
            min.setUTCDate(min.getUTCDate() - 7);
        } else if (this.default_range_selector === 2) {
            min.setUTCMonth(min.getUTCMonth() - 1);
        } else if (this.default_range_selector === 3) {
            min.setUTCMonth(min.getUTCMonth() - 3);
        } else if (this.default_range_selector === 4) {
            min.setUTCMonth(min.getUTCMonth() - 6);
        } else {
            min.setUTCFullYear(min.getUTCFullYear() - 1);
        }

        if (min < layer.minmaxdate_range.min) {
            min = layer.minmaxdate_range.min;
        }
        min = this._convertToDateWithData(layer, min);
        layer.date_range = {
            min: min,
            max: max
        };
        layer.currentdate = data.nearestTimeIso;
        // If map, also set extend to its bbox
        if (this.map && layer.autoExtent) {
            var southWest = L.latLng(data.bbox[1], data.bbox[0]);
            var northEast = L.latLng(data.bbox[3], data.bbox[2]);
            var bounds = L.latLngBounds(southWest, northEast);
            this.map.fitBounds(bounds);
        }
        // also save this variable units
        layer.units = data.units;
        if (callback !== undefined) {
            callback();
        }
    }).bind(this, layer));
};


NCWMSGridTimeseriesViewer.prototype.calculateMinMaxDate_ = function(layer) {
    if (this.map.timeDimension) {
        var times = this.map.timeDimension.getAvailableTimes();
        return {
            min: new Date(times[0]),
            max: new Date(times[times.length - 1])
        }
    }
    return this._calculateMinMaxDateFromDatsWithData(layer);
};

NCWMSGridTimeseriesViewer.prototype._calculateMinMaxDateFromDatsWithData = function(layer) {

    var minyear = null;
    var maxyear = null;
    var minmonth = null;
    var maxmonth = null;
    var minday = null;
    var maxday = null;

    for (var year in layer.datesWithData) {
        year = parseInt(year);
        if (minyear === null || year < minyear) minyear = year;
        if (maxyear === null || year > maxyear) maxyear = year;
    }

    for (var month in layer.datesWithData[minyear]) {
        month = parseInt(month);
        if (minmonth === null || month < minmonth) minmonth = month;
    }

    for (month in layer.datesWithData[maxyear]) {
        month = parseInt(month);
        if (maxmonth === null || month > maxmonth) maxmonth = month;
    }

    for (var day in layer.datesWithData[minyear][minmonth]) {
        day = parseInt(day);
        if (minday === null || layer.datesWithData[minyear][minmonth][day] < minday)
            minday = layer.datesWithData[minyear][minmonth][day];
    }

    for (var day in layer.datesWithData[maxyear][maxmonth]) {
        day = parseInt(day);
        if (maxday === null || layer.datesWithData[maxyear][maxmonth][day] > maxday)
            maxday = layer.datesWithData[maxyear][maxmonth][day];
    }

    var min = new Date(Date.UTC(minyear, minmonth, minday));
    min.setUTCDate(min.getUTCDate() + 1);
    return {
        min: min,
        max: new Date(Date.UTC(maxyear, maxmonth, maxday))
    };
};

NCWMSGridTimeseriesViewer.prototype._convertToDateWithData = function(layer, date) {
    if (this.map.timeDimension) {
        return new Date(this.map.timeDimension.seekNearestTime(date.getTime()));
    }
    return date;
};

NCWMSGridTimeseriesViewer.prototype.checkLoadNewData = function(layer, min, max) {
    min = new Date(min);
    max = new Date(max);
    if (!layer.date_range){
        return;
    }

    var afterLoadData = function(layer, serie, data) {
        if (data !== undefined)
            this.updateSerie(serie, data.time, data.values);
        layer.chart.hideLoading();
    };
    var i, l, serie;

    min = this._convertToDateWithData(layer, min);
    max = this._convertToDateWithData(layer, max);

    if (min < layer.date_range.min) {
        var old_min = layer.date_range.min;
        layer.date_range.min = min;
        layer.chart.showLoading();
        for (i = 0, l = layer.chart.series.length; i < l; i++) {
            serie = layer.chart.series[i];
            if (serie.options.custom && serie.options.custom.url)
                this._loadMoreData(layer, serie.options.custom.url, min, old_min, afterLoadData.bind(this, layer, serie));
        }
    }
    if (max > layer.date_range.max) {
        var old_max = layer.date_range.max;
        layer.date_range.max = max;
        layer.chart.showLoading();
        for (i = 0, l = layer.chart.series.length; i < l; i++) {
            serie = layer.chart.series[i];
            if (serie.options.custom && serie.options.custom.url)
                this._loadMoreData(layer, serie.options.custom.url, old_max, max, afterLoadData.bind(this, layer, serie));
        }
    }
};


NCWMSGridTimeseriesViewer.prototype.createMap = function(map) {
    var baseMaps = {};
    if (map) {
        this.map = map;
    } else {
        var mapOptions = {
            fullscreenControl: true,
            timeDimension: true,
            timeDimensionControl: true,
            center: [39.4, 2.9],
            zoom: 6
        };
        this.map = L.map(this.container, $.extend({}, mapOptions, this.mapOptions));

        if (this.baseMaps == undefined) {

            // Add OSM and emodnet bathymetry to map
            var osmLayer = L.tileLayer('http://{s}.tile.osm.org/{z}/{x}/{y}.png', {
                attribution: '&copy; <a href="http://osm.org/copyright">OpenStreetMap</a> contributors'
            });            
            var bathymetryLayer = L.tileLayer.wms("http://ows.emodnet-bathymetry.eu/wms", {
                layers: 'emodnet:mean_atlas_land',
                format: 'image/png',
                transparent: true,
                attribution: "<a href='http://www.emodnet-bathymetry.eu/'>EMODnet Bathymetry</a>",
                opacity: 0.8
            });
            var namesLayer = L.tileLayer.wms("http://ows.emodnet-bathymetry.eu/wms", {
                layers: 'world:sea_names',
                format: 'image/png',
                transparent: true,
                opacity: 0.3
            });
            var underseaLayer = L.tileLayer.wms("http://ows.emodnet-bathymetry.eu/wms", {
                layers: 'gebco:undersea_features',
                format: 'image/png',
                transparent: true,
                opacity: 0.3
            });            
            var coastlinesLayer = L.tileLayer.wms("http://ows.emodnet-bathymetry.eu/wms", {
                layers: 'coastlines',
                format: 'image/png',
                transparent: true,
                opacity: 0.8
            });

            
            var bathymetryGroupLayer = L.layerGroup([bathymetryLayer, coastlinesLayer, namesLayer, underseaLayer]);
            bathymetryGroupLayer.addTo(this.map);
            this.baseMaps = {
                "Emodnet bathymetry": bathymetryGroupLayer,
                "OSM": osmLayer
            };
        } else {
            for (var baselayer in this.baseMaps) {
                this.baseMaps[baselayer].addTo(this.map);
                break;
            }
        }
        L.control.coordinates({
            position: "bottomleft",
            decimals: 3,
            labelTemplateLat: "Latitude: {y}",
            labelTemplateLng: "Longitude: {x}",
            useDMS: true,
            enableUserInput: false
        }).addTo(this.map);
    }
    var overlayMaps = {};
    this.layerControl = L.control.layers(this.baseMaps, overlayMaps);
    this.layerControl.addTo(this.map);

    this.map.on('layeradd', function(eventLayer) {
        if (eventLayer.layer.legend) {
            eventLayer.layer.legend.addTo(this);
        }
    });

    this.map.on('layerremove', function(eventLayer) {
        if (eventLayer.layer.legend) {
            this.removeLayer(eventLayer.layer.legend);
            eventLayer.layer.legend.onRemove();
        }
    });

    this.map.doubleClickZoom.disable();
    this.map.on('layeradd', (function() {
        this.map.doubleClickZoom.disable();
    }).bind(this));
    this.map.on('dblclick', (function(e) {
        this.addPositionMarker({
            position: [e.latlng.lat, e.latlng.lng]
        });
        return false;
    }).bind(this));

    if (!this.map.timeDimension) {
        this.map.timeDimension = L.timeDimension({});
    }
    if (this._updateTimeDimension){
        this.map.timeDimension.on('availabletimeschanged', (function() {
            this.addDefaultMarkers();
        }).bind(this));        
    } else {
        this.addDefaultMarkers();
    }
};


NCWMSGridTimeseriesViewer.prototype.addLegend = function(layer, map) {
    var div_wrapper = L.DomUtil.get('legend-wrapper');
    if (!div_wrapper) {
        div_wrapper = L.DomUtil.create('div', 'legend-wrapper');
        div_wrapper.id = "legend-wrapper";
    }
    var styles = layer.params.styles;
    var palette = styles.substring(styles.indexOf('/') + 1);
    var colorscalerange = layer.params.colorscalerange || 'default';
    var div = L.DomUtil.create('div', 'info legend-div', div_wrapper);
    div.id = "legend-" + layer.params.layers;
    if (colorscalerange == 'auto') {
        // TODO: get colorscalerange
        return div_wrapper;
    }
    if (layer.legendHTML) {
        div.innerHTML = layer.legendHTML.apply();
    } else {
        var src = layer.url + "?SERVICE=WMS&VERSION=1.1.1&REQUEST=GetLegendGraphic&TRANSPARENT=true&LAYER=" + layer.params.layers + "&PALETTE=" + palette + "&COLORSCALERANGE=" + colorscalerange;
        if (layer.params.numcolorbands) {
            src += '&numcolorbands=' + layer.params.numcolorbands;
        }
        div.innerHTML +=
            '<img class="legend-img" src="' + src + '" alt="legend">';
    }

    return div_wrapper;
};

NCWMSGridTimeseriesViewer.prototype.removeLegend = function(layer, map) {
    var div = L.DomUtil.get("legend-" + layer.params.layers);
    div.remove();
    return;
};

NCWMSGridTimeseriesViewer.prototype.createChartContainer = function(layer) {
    var chart_wrapper = $('#' + this.container).parent().find('.chart-wrapper');
    if (!chart_wrapper.length) {
        $('#' + this.container).parent().append("<div class='chart-wrapper'></div>");
        chart_wrapper = $('#' + this.container).parent().find('.chart-wrapper');
    }
    var chart_container = chart_wrapper.find('.chart-' + layer.params.layers);
    if (!chart_container.length) {
        chart_wrapper.append("<div class='chart chart-" + layer.params.layers + "'></div>");        
    }    
};

NCWMSGridTimeseriesViewer.prototype.createChart = function(layer) {
    var chart_wrapper = $('#' + this.container).parent().find('.chart-wrapper');
    if (!chart_wrapper.length) {
        $('#' + this.container).parent().append("<div class='chart-wrapper'></div>");
        chart_wrapper = $('#' + this.container).parent().find('.chart-wrapper');
    }
    var chart_container = chart_wrapper.find('.chart-' + layer.params.layers);
    if (!chart_container.length) {
        chart_wrapper.append("<div class='chart chart-" + layer.params.layers + "'></div>");
        chart_container = chart_wrapper.find('.chart-' + layer.params.layers);
    }

    var options = {
        legend: {
            enabled: true,
        },

        chart: {
            zoomType: 'x'
        },
        rangeSelector: {
            selected: this.default_range_selector,
            buttons: [{
                type: 'day',
                count: 3,
                text: '3d'
            }, {
                type: 'day',
                count: 7,
                text: '7d'
            }, {
                type: 'month',
                count: 1,
                text: '1m'
            }, {
                type: 'month',
                count: 3,
                text: '3m'
            }, {
                type: 'month',
                count: 6,
                text: '6m'
            }, {
                type: 'year',
                count: 1,
                text: '1y'
            }, {
                type: 'all',
                text: 'All'
            }]
        },
        xAxis: {
            events: {
                afterSetExtremes: (function(layer, e) {
                    if (e.trigger != "updatedData")
                        this.checkLoadNewData(layer, e.min, e.max);
                }).bind(this, layer)
            },
            plotLines: [{
                color: 'red',
                dashStyle: 'solid',
                value: new Date(this.map.timeDimension.getCurrentTime()),
                width: 2,
                id: 'pbCurrentTime'
            }]
        },
        title: {
            text: layer.name
        },
        series: [],
        plotOptions: {
            series: {
                cursor: 'pointer',
                point: {
                    events: {
                        click: (function(event) {
                            var day = new Date(event.point.x);
                            this.map.timeDimension.setCurrentTime(day.getTime());
                        }).bind(this)
                    }
                }
            }
        }
    };

    if (layer.params.layers.substring(0, 3) == 'QC_') {
        options['yAxis'] = {};
        options['yAxis']['tickPositions'] = [0, 1, 2, 3, 4, 6, 9];
        options['yAxis']['plotBands'] = [{
            from: 0,
            to: 0.5,
            color: '#FFFFFF',
            label: {
                text: 'No QC performed',
                style: {
                    color: '#606060'
                }
            }
        }, {
            from: 0.5,
            to: 1.5,
            color: 'rgba(0, 255, 0, 0.5)',
            label: {
                text: 'Good data',
                style: {
                    color: '#606060'
                }
            }
        }, {
            from: 1.5,
            to: 2.5,
            color: 'rgba(0, 255, 0, 0.2)',
            label: {
                text: 'Probably good data',
                style: {
                    color: '#606060'
                }
            }
        }, {
            from: 2.5,
            to: 3.5,
            color: 'rgba(255, 0, 0, 0.2)',
            label: {
                text: 'Probably bad data',
                style: {
                    color: '#606060'
                }
            }
        }, {
            from: 3.5,
            to: 4.5,
            color: 'rgba(255, 0, 0, 0.5)',
            label: {
                text: 'Bad data',
                style: {
                    color: '#606060'
                }
            }
        }, {
            from: 5.5,
            to: 6.5,
            color: 'rgba(177, 11, 255, 0.5)',
            label: {
                text: 'Spike',
                style: {
                    color: '#606060'
                }
            }
        }, { // High wind
            from: 8.5,
            to: 9.5,
            color: 'rgba(200, 200, 200, 0.2)',
            label: {
                text: 'Missing value',
                style: {
                    color: '#606060'
                }
            }
        }];
    }

    if (layer.units == 'degree') {
        options['yAxis'] = {};
        options['yAxis']['tickPositions'] = [0, 90, 180, 270, 360, 361];
        options['yAxis']['labels'] = {
            formatter: function() {
                if (this.value == 0)
                    return 'N';
                if (this.value == 90)
                    return 'E';
                if (this.value == 180)
                    return 'S';
                if (this.value == 270)
                    return 'W';
                if (this.value == 360)
                    return 'N';
                return this.value;
            }
        };
        // options['chart']['type'] = 'heatmap';
    }

    if (layer.units == 'degrees') {
        options['yAxis'] = {};
        options['yAxis']['tickPositions'] = [-180, -90, 0, 90, 180];
    }

    chart_container.highcharts('StockChart', options);
    var chart = chart_container.highcharts()
    this.map.timeDimension.on('timeload', (function(data) {
        chart.xAxis[0].removePlotBand("pbCurrentTime");
        chart.xAxis[0].addPlotLine({
            color: 'red',
            dashStyle: 'solid',
            value: new Date(this.map.timeDimension.getCurrentTime()),
            width: 2,
            id: 'pbCurrentTime'
        });
    }).bind(this));
    return chart;
};

NCWMSGridTimeseriesViewer.prototype.addSerie = function(layer, time, variableData, position, url, color) {
    var serie = this.createSerie(layer, time, variableData, position, url, color);
    if (!layer.chart)
        layer.chart = this.createChart(layer);
    layer.chart.addSeries(serie);
    return serie.id;
};

NCWMSGridTimeseriesViewer.prototype.createSerie = function(layer, time, variableData, position, url, color) {
    var serieName = layer.name + ' at ' + position;
    if (this._sourceLegend){
        serieName = this._sourceLegend;
        if (position.trim().length){
            serieName += ' at ' +  position;
        }
    }
    return {
        name: serieName,
        type: 'line',
        id: Math.random().toString(36).substring(7),
        color: color,
        data: (function() {
            var length = time.length;
            var data = new Array(length);
            var this_time = new Date();
            var this_data = null;
            for (var i = 0; i < length; i++) {
                this_time = (new Date(time[i])).getTime();
                this_data = variableData[i];
                if (isNaN(this_data))
                    this_data = null;
                data[i] = [this_time, this_data];
            }
            return data.sort();
        })(),
        tooltip: {
            valueDecimals: 2,
            valueSuffix: ' ' + this._displayUnits(layer.units),
            xDateFormat: '%A, %b %e, %H:%M',
            headerFormat: '<span style="font-size: 12px; font-weight:bold;">{point.key} (Click to visualize the map on this time)</span><br/>'
        },
        custom: {
            variable: layer.name,
            position: position,
            url: url
        }
    };
};

NCWMSGridTimeseriesViewer.prototype._displayUnits = function(units){
    var display = units;
    display = display.replace(/(.*) ([\w])(-1)/, "$1/$2");    
    return display;
};


NCWMSGridTimeseriesViewer.prototype.updateSerie = function(serie, time, variableData) {
    var length = time.length;
    var new_data = new Array(length);
    var this_time = new Date();
    var this_data = null;
    for (var i = 0; i < length; i++) {
        this_time = (new Date(time[i])).getTime();
        this_data = variableData[i];
        if (isNaN(this_data))
            this_data = null;
        new_data[i] = [this_time, this_data];
    }
    var old_data = serie.options.data;
    serie.options.data = old_data.concat(new_data).sort();
    serie.setData(serie.options.data);
};


NCWMSGridTimeseriesViewer.prototype.removeLayer = function(layerName) {
    for (var i = 0, l = this.layers.length; i < l; i++) {
        var layer = this.layers[i];
        if (layer.name != layerName){
            continue;
        }
        if (layer.timeLayer){
            this.map.removeLayer(layer.timeLayer);
        }
        break;
    }
    return;
};