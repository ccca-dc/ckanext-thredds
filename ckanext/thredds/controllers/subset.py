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
import ckan.lib.navl.dictization_functions as df
import datetime
from ckan.common import _

from ckanapi import RemoteCKAN

get_action = logic.get_action
parse_params = logic.parse_params
tuplize_dict = logic.tuplize_dict
clean_dict = logic.clean_dict
check_access = logic.check_access

c = base.c
request = base.request
abort = base.abort
redirect = base.redirect
log = logging.getLogger(__name__)

NotAuthorized = logic.NotAuthorized
NotFound = logic.NotFound
Invalid = df.Invalid


class SubsetController(base.BaseController):
    resource = ""
    package = ""

    def create_subset(self, resource_id):
        print(resource_id)
        context = {'model': model, 'session': model.Session,
                   'user': c.user}

        global resource
        global package

        try:
            resource = toolkit.get_action('resource_show')(context, {'id': resource_id})
        except NotAuthorized:
            abort(403, _('Unauthorized to show resource'))
        except NotFound:
            abort(404, _('The resource {id} could not be found.'
                         ).format(id=resource_id))

        package = toolkit.get_action('package_show')(context, {'id': resource['package_id']})

        # check if user can download resource
        if authz.auth_is_anon_user(context) and resource.get('anonymous_download', 'false') == 'false':
            abort(401, _('Unauthorized to create subset of %s') % resource_id)

        # check if user is allowed to create package
        create_pkg = True
        try:
            check_access('package_create', context)
        except NotAuthorized:
            create_pkg = False

        return_layers = []

        demo = RemoteCKAN('https://sandboxdc.ccca.ac.at', apikey='')

        layers = demo.call_action('thredds_get_layers', {'id': '88d350e9-5e91-4922-8d8c-8857553d5d2f'})
        layer_details = demo.call_action('thredds_get_layerdetails',{'id':'88d350e9-5e91-4922-8d8c-8857553d5d2f','layer': layers[0]['children'][0]['id']})

        bbox = layer_details['bbox']

        for layer in layers[0]['children']:
            return_layers.append({'id': layer['id'], 'label': layer['label']})

        return toolkit.render('subset_create.html', {'title': 'Create Subset', 'layers': return_layers, 'bbox': bbox, 'create_pkg': create_pkg})

    def submit_subset(self):
        context = {'model': model, 'session': model.Session,
                   'user': c.user}

        global resource
        global package

        if authz.auth_is_anon_user(context) and resource.get('anonymous_download', 'false') == 'false':
            abort(401, _('Unauthorized to read resource %s') % id)

        title = request.params.get('title', '')
        layers = request.params.getall('layers')
        accept = request.params.get('accept')
        string_coordinates = request.params.get('coordinates', '')
        time_start = request.params.get('time_start', '')
        time_end = request.params.get('time_end', '')
        res_create = request.params.get('res_create', 'False')

        # start building URL with var (required) and accept (always has a value)
        url = "/tds_proxy/ncss/" + resource['id'] + "?var=" + layers[0] + '&accept=' + accept

        # adding time
        if time_start != "" and time_end != "":
            try:
                time_start = h.date_str_to_datetime(time_start).isoformat()
                time_end = h.date_str_to_datetime(time_end).isoformat()
                if time_end > time_start:
                    url = url + '&time_start=' + time_start + "&time_end=" + time_end
                else:
                    # swap times if start time before end time
                    url = url + '&time_start=' + time_end + "&time_end=" + time_start
            except (TypeError, ValueError), e:
                raise Invalid(_('Date format incorrect'))

        # adding coordinates
        if string_coordinates != "":
            try:
                coordinates = [float(n) for n in string_coordinates.split(",")]

                if len(coordinates) == 2:
                    url = url + "&latitude=" + str(coordinates[0]) + "&longitude=" + str(coordinates[1])
                elif len(coordinates) == 4 and coordinates[3] > coordinates[1] and coordinates[2] > coordinates[0]:
                    url = url + "&north=" + str(coordinates[3]) + "&south=" + str(coordinates[1]) + "&east=" + str(coordinates[2]) + "&west=" + str(coordinates[0])
            except Exception:
                # if coordinates are not correct, then they are simply not added
                pass

        print(url)

        # create resource if requested from user
        if res_create == 'True':
            try:
                check_access('package_create', context)
            except NotAuthorized:
                abort(403, _('Unauthorized to create a package'))

            ckan_url = config.get('ckan.site_url', '')

            new_package = package.copy()
            new_package.pop('id')
            new_package.pop('resources')
            new_package.pop('name')
            new_package['name'] = title
            new_package['private'] = True
            new_package['state'] = 'active'

            new_package = toolkit.get_action('package_create')(context, new_package)

            new_resource = toolkit.get_action('resource_create')(context, {'name': resource['name'] + '_subset', 'url': ckan_url + url, 'package_id': new_package['id']})
            redirect(h.url_for(controller='package', action='resource_read',
                               id=new_package['id'], resource_id=new_resource['id']))
        else:
            h.redirect_to(str(url))
