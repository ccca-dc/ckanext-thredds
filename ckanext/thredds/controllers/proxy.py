import ckan.lib.helpers as h
import ckan.lib.base as base
import requests
from urlparse import urlparse, parse_qs
from pylons import config
import ckan.plugins.toolkit as tk

import logging
import ckan.model as model
import ckan.logic as logic
import ckan.lib.uploader as uploader
import ckan.lib.navl.dictization_functions as dict_fns
from ckan.common import _, request, c, g, response

import ckan.authz as authz
import os

get_action = logic.get_action
parse_params = logic.parse_params
tuplize_dict = logic.tuplize_dict
clean_dict = logic.clean_dict

c = base.c
request = base.request
log = logging.getLogger(__name__)


class ThreddsProxyController(base.BaseController):
    def tds_proxy(self, service, catalog, res_id_1, res_id_2, res_id_3, **kwargs):
        """
        Provides a wms Service for netcdf files by redirecting the user to the
        thredds server

        """

        context = {'model': model, 'session': model.Session,
                   'user': c.user, 'auth_user_obj': c.userobj}

        res_id = res_id_1 + res_id_2 + res_id_3
        try:
           rsc = tk.get_action('resource_show')(context, {'id': res_id})
        except (tk.ObjectNotFound, tk.NotAuthorized):
           tk.abort(404, _('Resource not found'))

        if "wms" in service:
            p_query = request.query_string
            if 'extra' in kwargs:
                p_path = os.path.join('/tds_internal', service, catalog, res_id_1, res_id_2, res_id_3, kwargs.get('extra'))
            else:
                p_path = os.path.join('/tds_internal', service, catalog, res_id_1, res_id_2, res_id_3)

            response.headers['X-Accel-Redirect'] = "{0}?{1}".format(p_path,p_query)
            return response
        elif authz.auth_is_anon_user(context):
            tk.abort(401, _('Unauthorized to read resource %s') % res_id)
        else:
            p_query = request.query_string
            if 'extra' in kwargs:
                p_path = os.path.join('/tds_internal', service, catalog, res_id_1, res_id_2, res_id_3, kwargs.get('extra'))
            else:
                p_path = os.path.join('/tds_internal', service, catalog,res_id_1, res_id_2, res_id_3)

            response.headers['X-Accel-Redirect'] = "{0}?{1}".format(p_path,p_query)
            return response

