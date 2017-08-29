$('ul#querylist li').click( function() {
    var valQuoteChange = $(this).find('div:first').attr("value").replace(/'/g, '"');
    params = JSON.parse(valQuoteChange);
    for (param in params) {
        //if (params[param].match(/[a-z]/i)){
            if(param == "north"){
                $('#southWest').show();
                $('label[for="north"]').text("North");
                $('label[for="east"]').text("East");

                $('#north').val(params[param]);
            } else if(param == "latitude"){
                $('#south').val("");
                $('#west').val("");
                $('#southWest').hide();
                $('label[for="north"]').text("Latitude");
                $('label[for="east"]').text("Longitude");

                $('#north').val(params[param]);
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
        //}
    }
});

function myParser(str) {
    return str.slice(1, -1).split(',').map(function(el) {
        return el.trim()
    }).map(function(el) {
        return el.split('=')
    }).reduce(function(result, pair) {
        result[pair[0].trim()] = pair[1].trim();
        return result
    }, {});
}
