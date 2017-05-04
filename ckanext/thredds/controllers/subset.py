import ckan.lib.helpers as h
import ckan.lib.base as base
from urlparse import urlparse, parse_qs
from pylons import config
import ckan.plugins.toolkit as toolkit

import logging
import ckan.model as model
import ckan.logic as logic
import ckan.lib.uploader as uploader
import ckan.lib.navl.dictization_functions as dict_fns
import ckan.authz as authz

from ckanapi import RemoteCKAN

get_action = logic.get_action
parse_params = logic.parse_params
tuplize_dict = logic.tuplize_dict
clean_dict = logic.clean_dict
check_access = logic.check_access

c = base.c
request = base.request
abort = base.abort
log = logging.getLogger(__name__)

NotAuthorized = logic.NotAuthorized

class SubsetController(base.BaseController):
    resource = ""

    def create_subset(self, resource_id):
        print(resource_id)
        context = {'model': model, 'session': model.Session,
                   'user': c.user}

        global resource
        resource = toolkit.get_action('resource_show')(context, {'id': resource_id})
        package = toolkit.get_action('package_show')(context, {'id': resource['package_id']})

        return_layers = []

        demo = RemoteCKAN('https://sandboxdc.ccca.ac.at', apikey='')

        layers = demo.call_action('thredds_get_layers', {'id': '88d350e9-5e91-4922-8d8c-8857553d5d2f'})
        layer_details = demo.call_action('thredds_get_layerdetails',{'id':'88d350e9-5e91-4922-8d8c-8857553d5d2f','layer': layers[0]['children'][0]['id']})

        bbox = layer_details['bbox']

        for layer in layers[0]['children']:
            return_layers.append(layer['id'])

        is_anon = False

        if authz.auth_is_anon_user(context):
            is_anon = True

        return toolkit.render('subset_create.html', {'title': 'Create Subset', 'layers': return_layers, 'bbox': bbox, 'is_anon': is_anon})

    def submit_subset(self):
        context = {'model': model, 'session': model.Session,
                   'user': c.user}

        layers = request.params.getall('layers')
        accept = request.params.get('accept')
        coordinates = request.params.get('coordinates', '')
        date_from = request.params.get('date_from', '')
        date_to = request.params.get('date_to', '')
        res_create = request.params.get('res_create', False)

        url = "https://sandboxdc.ccca.ac.at/tds_proxy/ncss/" + resource['id'] + "?var=" + layers[0] + '&accept=' + accept

        if date_from != "" and date_to != "":
            url = url + '&date_from=' + date_from

        print(url)

        #if res_create:
        #    rsc = tk.get_action('package_create')(context, {'id': })
