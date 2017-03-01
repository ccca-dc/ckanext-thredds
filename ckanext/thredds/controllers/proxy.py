import ckan.lib.helpers as h
import ckan.lib.base as base
import requests
from pylons import config
import ckan.plugins.toolkit as toolkit

import logging
import ckan.model as model
import ckan.logic as logic
import ckan.lib.uploader as uploader
import ckan.lib.navl.dictization_functions as dict_fns

get_action = logic.get_action
parse_params = logic.parse_params
tuplize_dict = logic.tuplize_dict
clean_dict = logic.clean_dict

c = base.c
request = base.request
log = logging.getLogger(__name__)


class WMSProxyController(base.BaseController):
    def wms_proxy(self):
        url = request.params.get('url')
        r = requests.get(url)
#        if url.find("GetCapabilities") != -1:
#            log.debug(url)
#            log.debug(r.headers)
        return r.content

#$url = $_GET['url'];
#$result = "";
#if (strpos($url, "GetCapabilities") >= 0){
#    $result = file_get_contents($url);
#    $nlines = count($http_response_header);
#    for ($i = $nlines-1; $i >= 0; $i--) {
#        $line = $http_response_header[$i];
#        if (substr_compare($line, 'Content-Type', 0, 12, true) == 0) {
#            $content_type = $line;
#            break;
#        }
#    }
#    header($content_type);
#    echo $result;
#} else{
#    header('HTTP/1.0 400 Bad Request');
#    echo 'Request not valid';
#}
