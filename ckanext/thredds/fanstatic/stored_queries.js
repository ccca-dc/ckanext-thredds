$('ul#querylist li').click( function() {
    var params = $(this).text().split("\n");
    for (i = 0; i < params.length; i++) {
        if (params[i].match(/[a-z]/i)){
            split_param = $.trim(params[i]).split(': ')
            if($("[name='" + split_param[0] + "']").is(':radio') != true){
                $("[name='" + split_param[0] + "']").val(split_param[1]);
            }else{
                for (j = 0; j < $("[name='" + split_param[0] + "']").length; j++) {
                    if($("[name='" + split_param[0] + "']")[j].value.toLowerCase() ==split_param[1]){
                        $("[name='" + split_param[0] + "']")[j].checked=true;
                    }
                }
            }
        }
    }
});
