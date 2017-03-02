import ckan.lib.helpers as h
import ckan.lib.base as base
import requests
from urlparse import urlparse, parse_qs
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
        """
        Provides a direct download by either redirecting the user to the url
        stored or downloading an uploaded file directly.
        """
        context = {'model': model, 'session': model.Session,
                   'user': c.user, 'auth_user_obj': c.userobj}

        #try:
        #    rsc = get_action('resource_show')(context, {'id': resource_id})
        #except (NotFound, NotAuthorized):
        #    abort(404, _('Resource not found'))

        if authz.auth_is_anon_user(context):
            abort(401, _('Unauthorized to read resource %s') % resource_id)
        else:
            p_url = urlparse(request.params.get('url'))
            response.headers['X-Accel-Redirect'] = "{0}".format(p_url.path)
            return response
        #abort(404, _('No wms available'))
