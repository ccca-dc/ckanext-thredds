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
from ckan.common import _
import ast
import urllib
from dateutil.relativedelta import relativedelta

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
        try:
            check_access('resource_show', context, {'id': resource_id})
        except NotAuthorized:
            abort(403, _('Unauthorized to show resource'))
        except NotFound:
            abort(404, _('The resource {id} could not be found.'
                         ).format(id=resource_id))

        # check if user can download resource
        #if authz.auth_is_anon_user(context) and resource.get('anonymous_download', 'false') == 'false':
        if authz.auth_is_anon_user(context):
            abort(401, _('Unauthorized to create subset of %s') % resource_id)

        go_to_form = True

        resource = toolkit.get_action('resource_show')(context, {'id': resource_id})
        package = toolkit.get_action('package_show')(context, {'id': resource['package_id']})

        # Submit the data
        if 'save' in request.params:
            data, errors, error_summary = self._submit(context, resource, package)

            if len(errors) == 0:
                go_to_form = False
        else:
            data['all_layers'] = []

            try:
                layers = toolkit.get_action('thredds_get_layers')(context, {'id': resource['id']})
                layer_details = toolkit.get_action('thredds_get_layerdetails')(context, {'id': resource['id'], 'layer': layers[0]['children'][0]['id']})
            except Exception:
                h.flash_error("This resource cannot create a subset")
                redirect(h.url_for(controller='package', action='resource_read',
                                   id=package['id'], resource_id=resource['id']))

            data['bbox'] = layer_details['bbox']

            for layer in layers[0]['children']:
                data['all_layers'].append({'id': layer['id'], 'label': layer['label']})

        if go_to_form is True:
            # check if user is allowed to create package
            data['create_pkg'] = True
            try:
                check_access('package_create', context)
            except NotAuthorized:
                data['create_pkg'] = False

            data['pkg'] = package

            data['organizations'] = []
            for org in toolkit.get_action('organization_list_for_user')(context, {'permission': 'create_dataset'}):
                data['organizations'].append({'value': org['id'], 'text': org['display_name']})

            vars = {'data': data, 'errors': errors, 'error_summary': error_summary}
            return toolkit.render('subset_create.html', extra_vars=vars)

    @staticmethod
    def _submit(context, resource, package):
        data = logic.clean_dict(unflatten(logic.tuplize_dict(logic.parse_params(request.params))))

        data['bbox'] = [n[2:-1] for n in data['bbox'].replace('[', '').replace(']', '').split(", ")]
        data['all_layers'] = ast.literal_eval(str(data['all_layers']))

        errors = {}
        error_summary = {}

        # error section
        # error coordinate section, checking if values are entered and floats
        data['point'] = False
        northSouthOk = False
        eastWestOk = False
        if data['north'] != "" and data['east'] != "":
            try:
                float(data['north'])
                northSouthOk = True
            except (TypeError, ValueError):
                errors['north'] = [u'Coordinate incorrect']
                error_summary['north'] = u'Coordinate incorrect'
            try:
                float(data['east'])
                eastWestOk = True
            except (TypeError, ValueError):
                errors['east'] = [u'Coordinate incorrect']
                error_summary['east'] = u'Coordinate incorrect'

            if data['south'] != "" and data['west'] != "":
                try:
                    float(data['south'])
                except (TypeError, ValueError):
                    northSouthOk = False
                    errors['south'] = [u'Coordinate incorrect']
                    error_summary['south'] = u'Coordinate incorrect'
                try:
                    float(data['west'])
                except (TypeError, ValueError):
                    eastWestOk = False
                    errors['west'] = [u'Coordinate incorrect']
                    error_summary['west'] = u'Coordinate incorrect'
            elif data['south'] == "" and data['west'] == "":
                data['point'] = True
            elif data['south'] != "" and data['west'] == "":
                northSouthOk = False
                eastWestOk = False
                errors['west'] = [u'Missing value']
                error_summary['west'] = u'Missing value'
            elif data['south'] == "" and data['west'] != "":
                northSouthOk = False
                eastWestOk = False
                errors['south'] = [u'Missing value']
                error_summary['south'] = u'Missing value'
        elif data['north'] != "" and data['east'] == "":
            errors['east'] = [u'Missing value']
            error_summary['east'] = u'Add east or delete north coordinate'
        elif data['north'] == "" and data['east'] != "":
            errors['north'] = [u'Missing value']
            error_summary['north'] = u'Add north or delete east coordinate'

        # error coordinate section, checking if values are inside bbox
        if northSouthOk is True:
            northf = float(data['north'])
            if data['south'] != "":
                southf = float(data['south'])
                if northf > float(data['bbox'][3]) and southf > float(data['bbox'][3]):
                    error_summary['latitude coordinates'] = u'north and south are further north than bounding box of resource'
                    errors['north'] = [u'coordinate is further north than bounding box of resource']
                    errors['south'] = [u'coordinate is further north than bounding box of resource']
                if northf < float(data['bbox'][1]) and southf < float(data['bbox'][1]):
                    error_summary['latitude coordinates'] = u'north and south are further south than bounding box of resource'
                    errors['north'] = [u'coordinate is further south than bounding box of resource']
                    errors['south'] = [u'coordinate is further south than bounding box of resource']
            else:
                if northf > float(data['bbox'][3]):
                    errors['north'] = [u'latitude is further north than bounding box of resource']
                    error_summary['latitude'] = u'coordinate is further north than bounding box of resource'
                if northf < float(data['bbox'][1]):
                    errors['north'] = [u'latitude is further south than bounding box of resource']
                    error_summary['latitude'] = u'coordinate is further south than bounding box of resource'

        if eastWestOk is True:
            eastf = float(data['east'])
            if data['west'] != "":
                westf = float(data['west'])
                if eastf > float(data['bbox'][2]) and westf > float(data['bbox'][2]):
                    error_summary['longitude coordinates'] = u'east and west coordinates are further east than bounding box of resource'
                    errors['east'] = [u'coordinate is further east than bounding box of resource']
                    errors['west'] = [u'coordinate is further east than bounding box of resource']
                if eastf < float(data['bbox'][0]) and westf < float(data['bbox'][0]):
                    error_summary['longitude coordinates'] = u'east and west coordinates are further west than bounding box of resource'
                    errors['east'] = [u'coordinate is further west than bounding box of resource']
                    errors['west'] = [u'coordinate is further west than bounding box of resource']
            else:
                if eastf > float(data['bbox'][2]):
                    errors['east'] = [u'longitude is further east than bounding box of resource']
                    error_summary['longitude'] = u'coordinate is further east than bounding box of resource'
                if eastf < float(data['bbox'][0]):
                    errors['east'] = [u'longitude is further west than bounding box of resource']
                    error_summary['longitude'] = u'coordinate is further west than bounding box of resource'

        # error layer section
        if 'layers' not in data or data["layers"] == '':
            errors['layers'] = [u'Missing Value']
            error_summary['layers'] = u'Missing value'

        # error resource creation section
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

        # error time section
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
                error_summary['time'] = u'The provided time range must intersect the dataset time range'

            if abs(relativedelta(given_end, given_start).years) > 5:
                errors['time_start'] = [u'Change time range']
                errors['time_end'] = [u'Change time range']
                error_summary['time'] = u'Currently we only support time ranges lower than 6 years'

        if data['time_start'] != "" and data['time_end'] == "":
            errors['time_end'] = [u'Missing value']
            error_summary['time end'] = u'Add end time or delete start time'

        if data['time_start'] == "" and data['time_end'] != "":
            errors['time_start'] = [u'Missing value']
            error_summary['time start'] = u'Add start time or delete end time'

        # end of error section
        if len(errors) == 0:
            # start building URL params with var (required)
            if type(data['layers']) is list:
                params = {'var': ','.join(data['layers'])}
            else:
                params = {'var': data['layers']}

            # adding accept (always has a value)
            params['accept'] = data['accept']

            # adding time
            if times_exist is True:
                try:
                    time_start = h.date_str_to_datetime(data['time_start']).isoformat()
                    time_end = h.date_str_to_datetime(data['time_end']).isoformat()
                    if time_end < time_start:
                        # swap times if start time before end time
                        data['time_start'], data['time_end'] = data['time_end'], data['time_start']
                    params['time_start'] = time_start
                    params['time_end'] = time_end
                except (TypeError, ValueError):
                    raise Invalid(_('Date format incorrect'))

            # adding coordinates
            if data['north'] != "" and data['east'] != "":
                if data['point'] is True:
                    params['latitude'] = data['north']
                    params['longitude'] = data['east']
                else:
                    params['north'] = data['north']
                    params['south'] = data['south']
                    params['east'] = data['east']
                    params['west'] = data['west']

            url = ('/tds_proxy/ncss/%s?%s' % (resource['id'], urllib.urlencode(params)))

            # create resource if requested from user
            if data['res_create'] == 'True':
                try:
                    check_access('package_show', context, {'id': package['id']})
                except NotAuthorized:
                    abort(403, _('Unauthorized to show package'))

                ckan_url = config.get('ckan.site_url', '')
                url_for_res = ckan_url + url

                # creating new package from the current one with few changes
                new_package = dict(package)
                new_package.pop('id')
                new_package.pop('resources')
                new_package['owner_org'] = data['organization']
                new_package['name'] = data['name']
                new_package['title'] = data['title']
                new_package['private'] = data['private']

                # add bbox if added
                if 'north' in params:
                    new_package['iso_northBL'] = params['north']
                    new_package['iso_southBL'] = params['south']
                    new_package['iso_eastBL'] = params['east']
                    new_package['iso_westBL'] = params['west']

                # add time if added
                if times_exist is True:
                    new_package['iso_exTempStart'] = data['time_start']
                    new_package['iso_exTempEnd'] = data['time_end']

                # add subset creator
                new_package['contact_info'] = ast.literal_eval(package['contact_info'])
                new_package['contact_info'].extend([context['auth_user_obj'].fullname, "", context['auth_user_obj'].email, "Subset Creator"])

                # need to pop package otherwise it overwrites the current pkg
                context.pop('package')

                new_package = toolkit.get_action('package_create')(context, new_package)
                new_resource = toolkit.get_action('resource_create')(context, {'name': resource['name'], 'url': url_for_res, 'package_id': new_package['id'], 'format': data['accept']})

                toolkit.get_action('package_relationship_create')(context, {'subject': new_package['id'], 'object': package['id'], 'type': 'child_of'})

                redirect(h.url_for(controller='package', action='resource_read',
                                   id=new_package['id'], resource_id=new_resource['id']))
            else:
                # redirect to url if user doesn't want to create a package
                h.redirect_to(str(url))

        return data, errors, error_summary
