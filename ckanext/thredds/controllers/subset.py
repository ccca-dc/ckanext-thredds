import ckan.lib.helpers as h
import ckan.lib.base as base
from urlparse import urlparse, parse_qs
from pylons import config
import ckan.plugins.toolkit as toolkit

import logging
import ckan.model as model
from ckan.model import (PACKAGE_NAME_MIN_LENGTH, PACKAGE_NAME_MAX_LENGTH)
import ckan.logic as logic
import ckan.lib.uploader as uploader
import ckan.lib.navl.dictization_functions as dict_fns
import ckan.authz as authz
import ckan.lib.navl.dictization_functions as df
import datetime
from ckan.common import _
import json
import ast

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

unflatten = df.unflatten


class SubsetController(base.BaseController):
    resource = ""
    package = ""

    def create_subset(self, resource_id):

        """
        Return a contact form
        :return: html
        """

        data = {}
        errors = {}
        error_summary = {}

        context = {'model': model, 'session': model.Session,
                   'user': c.user}

        # check if user can perform a resource_show
        '''try:
            check_access('resource_show', context)
            check_access('package_show', context)
        except NotAuthorized:
            abort(403, _('Unauthorized to show resource'))'''

        # check if user can download resource
        if authz.auth_is_anon_user(context) and resource.get('anonymous_download', 'false') == 'false':
            abort(401, _('Unauthorized to create subset of %s') % resource_id)

        go_to_form = False
        # Submit the data
        if 'save' in request.params:
            data, errors, error_summary = self._submit(context)

            if len(errors) != 0:
                go_to_form = True
        else:
            global resource
            global package

            go_to_form = True

            try:
                resource = toolkit.get_action('resource_show')(context, {'id': resource_id})
            except NotFound:
                abort(404, _('The resource {id} could not be found.'
                             ).format(id=resource_id))
            package = toolkit.get_action('package_show')(context, {'id': resource['package_id']})

            data['all_layers'] = []

            demo = RemoteCKAN('https://sandboxdc.ccca.ac.at', apikey='84f6bce7-da4b-465b-8303-3a86ab64084b')

            layers = demo.call_action('thredds_get_layers', {'id': '88d350e9-5e91-4922-8d8c-8857553d5d2f'})
            layer_details = demo.call_action('thredds_get_layerdetails',{'id':'88d350e9-5e91-4922-8d8c-8857553d5d2f','layer': layers[0]['children'][0]['id']})

            data['bbox'] = layer_details['bbox']

            for layer in layers[0]['children']:
                data['all_layers'].append({'id': layer['id'], 'label': layer['label']})

            data['all_layers'].append({'id': 'test', 'label': 'test'})

        if go_to_form is True:
            # check if user is allowed to create package
            data['create_pkg'] = True
            try:
                check_access('package_create', context)
            except NotAuthorized:
                data['create_pkg'] = False

            data['pkg'] = package

            vars = {'data': data, 'errors': errors, 'error_summary': error_summary}
            return toolkit.render('subset_create.html', extra_vars=vars)

    @staticmethod
    def _submit(context):
        data = logic.clean_dict(unflatten(logic.tuplize_dict(logic.parse_params(request.params))))

        data['bbox'] = [n[2:-1] for n in data['bbox'].replace('[', '').replace(']', '').split(", ")]
        data['all_layers'] = ast.literal_eval(str(data['all_layers']))

        global resource
        global package

        errors = {}
        error_summary = {}

        # error section
        if 'layers' not in data or data["layers"] == '':
            errors['layers'] = [u'Missing Value']
            error_summary['layers'] = u'Missing value'

        if data['res_create'] == 'True':
            if data['title'] == '':
                errors['title'] = [u'Missing Value']
                error_summary['title'] = u'Missing value'
            if data['name'] == '':
                errors['name'] = [u'Missing Value']
                error_summary['name'] = u'Missing value'
            else:
                try:
                    toolkit.get_action('package_show')(context, {'id': data['name']})

                    errors['name'] = [u'That URL is already in use.']
                    error_summary['name'] = u'That URL is already in use.'
                except NotFound:
                    pass

                if len(data['name']) < PACKAGE_NAME_MIN_LENGTH:
                    errors['name'] = [u'URL is too short.']
                    error_summary['name'] = _('length is less than minimum %s') % (PACKAGE_NAME_MIN_LENGTH)
                if len(data['name']) > PACKAGE_NAME_MAX_LENGTH:
                    errors['name'] = [u'URL is too long.']
                    error_summary['name'] = _('length is more than maximum %s') % (PACKAGE_NAME_MAX_LENGTH)

        times_exist = False
        if data['time_start'] != "" and data['time_end'] != "":
            times_exist = True
            given_start = h.date_str_to_datetime(data['time_start'])
            given_end = h.date_str_to_datetime(data['time_end'])
            package_start = h.date_str_to_datetime(package['iso_exTempStart'])
            package_end = h.date_str_to_datetime(package['iso_exTempEnd'])
            if given_start > package_end and given_end > package_end:
                errors['time_start'] = [u'Time is after maximum']
                errors['time_end'] = [u'Time is after maximum']
                error_summary['time'] = u'The provided time range must intersect the dataset time range'
            if given_start < package_start and given_end < package_start:
                errors['time_start'] = [u'Time is before minimum']
                errors['time_end'] = [u'Time is before minimum']
                error_summary['time'] = u'The provided time range must intersect the dataset time range '

        if data['time_start'] != "" and data['time_end'] == "":
            errors['time_end'] = [u'Missing value']
            error_summary['time end'] = u'Add end time or delete start time'

        if data['time_start'] == "" and data['time_end'] != "":
            errors['time_start'] = [u'Missing value']
            error_summary['time start'] = u'Add start time or delete end time'

        if len(errors) == 0:
            # start building URL with var (required)
            if type(data['layers']) is list:
                url = "/tds_proxy/ncss/" + resource['id'] + "?var=" + ','.join(data['layers'])
            else:
                url = "/tds_proxy/ncss/" + resource['id'] + "?var=" + data['layers']

            # adding accept (always has a value)
            url = url + '&accept=' + data['accept']


            # adding time
            if times_exist is True:
                try:
                    time_start = h.date_str_to_datetime(data['time_start']).isoformat()
                    time_end = h.date_str_to_datetime(data['time_end']).isoformat()
                    if time_end < time_start:
                        # swap times if start time before end time
                        data['time_start'], data['time_end'] = data['time_end'], data['time_start']
                    time_start = h.date_str_to_datetime(data['time_start']).isoformat()
                    time_end = h.date_str_to_datetime(data['time_end']).isoformat()
                    url = url + '&time_start=' + time_start + "&time_end=" + time_end
                except (TypeError, ValueError):
                    raise Invalid(_('Date format incorrect'))

            # adding coordinates
            if data['coordinates'] != "":
                try:
                    coordinates = [float(n) for n in data['coordinates'].split(",")]

                    if len(coordinates) == 2:
                        url = url + "&latitude=" + str(coordinates[0]) + "&longitude=" + str(coordinates[1])
                    elif len(coordinates) == 4 and coordinates[3] > coordinates[1] and coordinates[2] > coordinates[0]:
                        url = url + "&north=" + str(coordinates[3]) + "&south=" + str(coordinates[1]) + "&east=" + str(coordinates[2]) + "&west=" + str(coordinates[0])
                except Exception:
                    # if coordinates are not correct, then they are simply not added
                    pass

            # create resource if requested from user
            if data['res_create'] == 'True':
                try:
                    check_access('package_show', context, {'id': package['id']})
                except NotAuthorized:
                    abort(403, _('Unauthorized to show package'))

                ckan_url = config.get('ckan.site_url', '')

                # creating new package from the current one with few changes
                new_package = dict(package)
                new_package.pop('id')
                new_package.pop('resources')
                new_package['name'] = data['name']
                new_package['title'] = data['title']
                new_package['private'] = True

                # need to pop package otherwise it overwrites the current pkg
                context.pop('package')

                if times_exist is True:
                    new_package['iso_exTempStart'] = data['time_start']
                    new_package['iso_exTempEnd'] = data['time_end']

                new_package = toolkit.get_action('package_create')(context, new_package)

                new_resource = toolkit.get_action('resource_create')(context, {'name': resource['name'], 'url': ckan_url + url, 'package_id': new_package['id']})
                redirect(h.url_for(controller='package', action='resource_read',
                                   id=new_package['id'], resource_id=new_resource['id']))
            else:
                # redirect to url if user doesn't want to create a package
                h.redirect_to(str(url))

        return data, errors, error_summary
