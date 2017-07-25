# encoding: utf-8

import ckan.plugins.toolkit as tk
import ckan.logic
from owslib.wms import WebMapService
import os
import requests
import json
import ckan.plugins.toolkit as toolkit
import ckan.lib.helpers as h
import ckan.logic as logic
from ckan.model import (PACKAGE_NAME_MIN_LENGTH, PACKAGE_NAME_MAX_LENGTH)
from dateutil.relativedelta import relativedelta
from ckan.common import _
import ckan.lib.navl.dictization_functions as df
import urllib
import ast
import ckan.lib.base as base
from pylons import config
import datetime

check_access = logic.check_access

_get_or_bust = logic.get_or_bust

abort = base.abort

NotAuthorized = logic.NotAuthorized
NotFound = logic.NotFound
Invalid = df.Invalid
ValidationError = logic.ValidationError


@ckan.logic.side_effect_free
def thredds_get_layers(context, data_dict):
    '''Return the layers of a resource from Thredds WMS.
    Exclude lat, lon, latitude, longitude, x, y

    :param: the id of the resource
    :type id: string
    :rtype: list
    '''

    # Resource ID
    model = context['model']
    user = context['auth_user_obj']

    resource_id = tk.get_or_bust(data_dict,'id')
    resource = toolkit.get_action('resource_show')(context, {'id': resource_id})

    # Get URL for WMS Proxy
    ckan_url = config.get('ckan.site_url', '')
    wms_url = ckan_url + '/tds_proxy/wms/' + resource_id

    # Headers and payload for thredds request
    try:
        headers={'Authorization':user.apikey}
    except:
        raise NotAuthorized

    payload={'item':'menu',
             'request':'GetMetadata'}

    # Thredds request
    try:
        r = requests.get(wms_url, params=payload, headers=headers)
        layer_tds = json.loads(r.content)
    except Exception as e:
        raise NotFound("Thredds Server can not provide layer information for the resource")

    # Filter Contents
    layers_filter = []
    for idx,childa in enumerate(layer_tds['children']):
        layers_filter.append(dict())
        layers_filter[idx]['label'] = childa.get('label','')
        layers_filter[idx]['children'] = ([el for el in childa['children']
                                           if el['id'] not in ['lat','lon','latitude','longitude','x','y']])

    return layers_filter


@ckan.logic.side_effect_free
def thredds_get_layerdetails(context, data_dict):
    '''Return the details of the resources layer

    :param id: the id or name of the resource
    :type id: string
    :param layer: the layer name for the requested resources
    :type layer: string
    :rtype: dict
    '''

    # Resource ID
    model = context['model']
    user = context['auth_user_obj']

    resource_id = tk.get_or_bust(data_dict,'id')
    layer_name = tk.get_or_bust(data_dict,'layer')


    # Get URL for WMS Proxy
    ckan_url = config.get('ckan.site_url', '')
    wms_url = ckan_url + '/tds_proxy/wms/' + resource_id

    try:
        headers={'Authorization':user.apikey}
    except:
        raise NotAuthorized

    payload={'item':'layerDetails',
             'layerName':layer_name,
             'request':'GetMetadata'}

    try:
        r = requests.get(wms_url, params=payload, headers=headers)
        layer_details = json.loads(r.content)
    except Exception as e:
        raise NotFound("Thredds Server can not provide layer details")

    if 'exception' in layer_details:
        raise NotFound("Thredds Server can not provide layer details")

    try:
        del layer_details['datesWithData']
    except:
        pass

    return layer_details


@ckan.logic.side_effect_free
def subset_create(context, data_dict):
    '''Return the details of the resources layer

    :param id: the id of the resource of which a subset is to be created
    :param layers: list of layer ids that should be included in the subset
    :param accept: format of the subset (NetCDF, XML or CSV)
    :param res_create: true if dataset with resource should be created, false
        if subset should just be downloaded (optional, default = False)
    :param private: the visibility of the package (optional, default = True)
    :param organization: id or name of the organization, which is owner of the
        dataset (needed if res_create = True)
    :param name: name of the created dataset (required if res_create = True)
    :param title: title of the created dataset (required if res_create = True)
    :param north: northern degree if bbox or latitude if point (optional)
    :param east: eastern degree if bbox or longitude if point (optional)
    :param south: southern degree if bbox (optional)
    :param west: western degree if bbox (optional)
    :param time_start: start of time (optional)
    :param time_end: end of time (optional)
    :rtype: dictionary
    '''

    errors = {}

    id = _get_or_bust(data_dict, 'id')
    resource = toolkit.get_action('resource_show')(context, {'id': id})
    package = toolkit.get_action('package_show')(context, {'id': resource['package_id']})
    toolkit.get_action('organization_show')(context, {'id': data_dict['organization']})

    layers = toolkit.get_action('thredds_get_layers')(context, {'id': resource['id']})
    layer_details = toolkit.get_action('thredds_get_layerdetails')(context, {'id': resource['id'], 'layer': layers[0]['children'][0]['id']})

    bbox = layer_details['bbox']

    # error section
    # error coordinate section, checking if values are entered and floats
    data_dict['point'] = False
    northSouthOk = False
    eastWestOk = False
    if data_dict.get('north', "") != "" and data_dict.get('east', "") != "":
        try:
            float(data_dict['north'])
            northSouthOk = True
        except (TypeError, ValueError):
            errors['north'] = [u'Coordinate incorrect']
        try:
            float(data_dict['east'])
            eastWestOk = True
        except (TypeError, ValueError):
            errors['east'] = [u'Coordinate incorrect']

        if data_dict.get('south', "") != "" and data_dict.get('west', "") != "":
            try:
                float(data_dict['south'])
            except (TypeError, ValueError):
                northSouthOk = False
                errors['south'] = [u'Coordinate incorrect']
            try:
                float(data_dict['west'])
            except (TypeError, ValueError):
                eastWestOk = False
                errors['west'] = [u'Coordinate incorrect']
        elif data_dict.get('south', "") == "" and data_dict.get('west', "") == "":
            data_dict['point'] = True
        elif data_dict.get('south', "") != "" and data_dict.get('west', "") == "":
            northSouthOk = False
            eastWestOk = False
            errors['west'] = [u'Missing value']
        elif data_dict.get('south', "") == "" and data_dict.get('west', "") != "":
            northSouthOk = False
            eastWestOk = False
            errors['south'] = [u'Missing value']
    elif data_dict.get('north', "") != "" and data_dict.get('east', "") == "":
        errors['east'] = [u'Missing value']
    elif data_dict.get('north', "") == "" and data_dict.get('east', "") != "":
        errors['north'] = [u'Missing value']

    # error coordinate section, checking if values are inside bbox
    if northSouthOk is True:
        northf = float(data_dict['north'])
        if data_dict.get('south', "") != "":
            southf = float(data_dict['south'])
            if northf > float(bbox[3]) and southf > float(bbox[3]):
                errors['north'] = [u'coordinate is further north than bounding box of resource']
                errors['south'] = [u'coordinate is further north than bounding box of resource']
            elif northf < float(bbox[1]) and southf < float(bbox[1]):
                errors['north'] = [u'coordinate is further south than bounding box of resource']
                errors['south'] = [u'coordinate is further south than bounding box of resource']

            if northf > float(bbox[3]):
                data_dict['north'] = bbox[3]
            if southf < float(bbox[1]):
                data_dict['south'] = bbox[1]
        else:
            if northf > float(bbox[3]):
                errors['north'] = [u'latitude is further north than bounding box of resource']
            if northf < float(bbox[1]):
                errors['north'] = [u'latitude is further south than bounding box of resource']

    if eastWestOk is True:
        eastf = float(data_dict['east'])
        if data_dict.get('west', "") != "":
            westf = float(data_dict['west'])
            if eastf > float(bbox[2]) and westf > float(bbox[2]):
                errors['east'] = [u'coordinate is further east than bounding box of resource']
                errors['west'] = [u'coordinate is further east than bounding box of resource']
            elif eastf < float(bbox[0]) and westf < float(bbox[0]):
                errors['east'] = [u'coordinate is further west than bounding box of resource']
                errors['west'] = [u'coordinate is further west than bounding box of resource']

            if eastf > float(bbox[2]):
                data_dict['east'] = bbox[2]
            if westf < float(bbox[0]):
                data_dict['west'] = bbox[0]
        else:
            if eastf > float(bbox[2]):
                errors['east'] = [u'longitude is further east than bounding box of resource']
            if eastf < float(bbox[0]):
                errors['east'] = [u'longitude is further west than bounding box of resource']

    # error resource creation section
    if data_dict.get('type', 'download').lower() == 'new_package':
        if data_dict.get('title', "") == '':
            errors['title'] = [u'Missing Value']
        if data_dict.get('name', "") == '':
            errors['name'] = [u'Missing Value']
        else:
            try:
                toolkit.get_action('package_show')(context, {'id': data_dict['name']})

                errors['name'] = [u'That URL is already in use.']
            except NotFound:
                pass

            if len(data_dict['name']) < PACKAGE_NAME_MIN_LENGTH:
                errors['name'] = [u'URL is shorter than minimum (' + str(PACKAGE_NAME_MIN_LENGTH) + u')']
            if len(data_dict['name']) > PACKAGE_NAME_MAX_LENGTH:
                errors['name'] = [u'URL is longer than maximum (' + str(PACKAGE_NAME_MAX_LENGTH) + u')']
        if data_dict.get('organization', "") == '':
            errors['organization'] = [u'Missing Value']
    elif data_dict.get('type', 'download').lower() == 'existing_package':
        if data_dict.get('existing_package_id', "") == '':
            errors['existing_package_id'] = [u'Missing Value']
        else:
            try:
                toolkit.get_action('package_show')(context, {'id': data_dict['existing_package_id']})
                check_access('package_update', context, {'id': data_dict['existing_package_id']})
            except NotFound:
                errors['existing_package_id'] = [u'Package not found']
            except NotAuthorized:
                errors['existing_package_id'] = [u'Not authorized to add subset to this package']

    # error time section
    times_exist = False
    if data_dict.get('time_start', "") != "" and data_dict.get('time_end', "") != "":
        times_exist = True
        try:
            given_start = h.date_str_to_datetime(data_dict['time_start'])
        except (TypeError, ValueError):
            errors['time_start'] = [u'Time is incorrect']
            times_exist = False
        try:
            given_end = h.date_str_to_datetime(data_dict['time_end'])
        except (TypeError, ValueError):
            errors['time_end'] = [u'Time is incorrect']
            times_exist = False
        if 'iso_exTempStart' in package and 'iso_exTempEnd' in package and times_exist is True:
            package_start = h.date_str_to_datetime(package['iso_exTempStart'])
            package_end = h.date_str_to_datetime(package['iso_exTempEnd'])
            if given_start > package_end and given_end > package_end:
                errors['time_start'] = [u'Time is after maximum']
                errors['time_end'] = [u'Time is after maximum']
            elif given_start < package_start and given_end < package_start:
                errors['time_start'] = [u'Time is before minimum']
                errors['time_end'] = [u'Time is before minimum']

            if given_end > package_end:
                data_dict['time_end'] = str(package_end)
            if given_start < package_start:
                data_dict['time_start'] = str(package_start)

            # currently only 5 year ranges are permitted
            if abs(relativedelta(given_end, given_start).years) > 5:
                errors['time_start'] = [u'Currently we only support time ranges lower than 6 years']
                errors['time_end'] = [u'Currently we only support time ranges lower than 6 years']
    elif data_dict.get('time_start', "") != "" and data_dict.get('time_end', "") == "":
        errors['time_end'] = [u'Missing value']
    elif data_dict.get('time_start', "") == "" and data_dict.get('time_end', "") != "":
        errors['time_start'] = [u'Missing value']

    # error format section
    if data_dict.get('accept', "") != "":
        if data_dict['point'] is True and data_dict['accept'].lower() not in {'netcdf', 'csv', 'xml'}:
            errors['accept'] = [u'Wrong format']
        elif data_dict['point'] is False and data_dict['accept'].lower() != 'netcdf':
            errors['accept'] = [u'Wrong format']
    else:
        errors['accept'] = [u'Missing value']

    # error layer section
    if data_dict.get('layers', "") != "":
        if type(data_dict['layers']) is list:
            for l in data_dict['layers']:
                if not any(child['id'] == l for child in layers[0]['children']):
                    errors['layers'] = [u'layer "' + l + '" does not exist']
        else:
            if not any(child['id'] == data_dict['layers'] for child in layers[0]['children']):
                errors['layers'] = [u'layer "' + data_dict['layers'] + '" does not exist']
    else:
        errors['layers'] = [u'Missing value']

    # end of error section
    if len(errors) > 0:
        raise ValidationError(errors)
    else:
        # start building URL params with var (required)
        if type(data_dict['layers']) is list:
            params = {'var': ','.join(data_dict['layers'])}
        else:
            params = {'var': data_dict['layers']}

        # adding accept (always has a value)
        params['accept'] = data_dict['accept'].lower()

        # adding time
        if times_exist is True:
            time_start = h.date_str_to_datetime(data_dict['time_start']).isoformat()
            time_end = h.date_str_to_datetime(data_dict['time_end']).isoformat()
            if time_end < time_start:
                # swap times if start time before end time
                data_dict['time_start'], data_dict['time_end'] = data_dict['time_end'], data_dict['time_start']
            params['time_start'] = time_start
            params['time_end'] = time_end

        # adding coordinates
        if data_dict.get('north', "") != "" and data_dict.get('east', "") != "":
            if data_dict['point'] is True:
                params['latitude'] = round(float(data_dict['north']), 4)
                params['longitude'] = round(float(data_dict['east']), 4)
            else:
                params['north'] = round(float(data_dict['north']), 4)
                params['south'] = round(float(data_dict['south']), 4)
                params['east'] = round(float(data_dict['east']), 4)
                params['west'] = round(float(data_dict['west']), 4)

        ckan_url = config.get('ckan.site_url', '')
        url = ('%s/tds_proxy/ncss/%s?%s' % (ckan_url, resource['id'], urllib.urlencode(params)))

        return_dict = dict()

        # create resource if requested from user
        if data_dict.get('type', 'download').lower() in {'new_package', 'existing_package'}:
            try:
                check_access('package_show', context, {'id': package['id']})
            except NotAuthorized:
                abort(403, _('Unauthorized to show package'))

            # check if url already exists
            search_results = toolkit.get_action('resource_search')(context, {'query': "url:" + url})

            # check if private is true or false otherwise set private = "True"
            if 'private' not in data_dict or data_dict['private'].lower() not in {'true', 'false'}:
                data_dict['private'] = 'True'

            # creating new package from the current one with few changes
            if data_dict.get('type', 'download').lower() == 'new_package':
                if search_results['count'] > 0:
                    return_dict['existing_resource'] = toolkit.get_action('resource_show')(context, {'id': search_results['results'][0]['id']})
                    if data_dict.get('private', 'True').lower() == 'false':
                        return return_dict

                new_package = package.copy()
                new_package.pop('id')
                new_package.pop('resources')
                new_package.pop('groups')
                new_package.pop('revision_id')

                new_package['iso_mdDate'] = new_package['metadata_created'] = new_package['metadata_modified'] = datetime.datetime.now()
                new_package['owner_org'] = data_dict['organization']
                new_package['name'] = data_dict['name']
                new_package['title'] = data_dict['title']
                new_package['private'] = data_dict['private']

                # add bbox and spatial if added
                if 'north' in params:
                    n = params['north']
                    s = params['south']
                    e = params['east']
                    w = params['west']

                    new_package['iso_northBL'] = n
                    new_package['iso_southBL'] = s
                    new_package['iso_eastBL'] = e
                    new_package['iso_westBL'] = w

                    coordinates = [[w, s], [e, s], [e, n], [w, n], [w, s]]
                    spatial = ('{"type": "MultiPolygon", "coordinates": [[' + str(coordinates) + ']]}')

                    new_package['spatial'] = spatial

                # add time if added
                if times_exist is True:
                    new_package['iso_exTempStart'] = data_dict['time_start']
                    new_package['iso_exTempEnd'] = data_dict['time_end']

                # add subset creator
                new_package['contact_info'] = []
                if 'contact_info' in package:
                    new_package['contact_info'] = ast.literal_eval(package['contact_info'])
                new_package['contact_info'].extend([context['auth_user_obj'].fullname, "", context['auth_user_obj'].email, "Subset Creator"])

                # need to pop package otherwise it overwrites the current pkg
                context.pop('package')

                new_package = toolkit.get_action('package_create')(context, new_package)
                package_to_add_id = new_package['id']
            else:
                package_to_add_id = data_dict['existing_package_id']
                existing_package = toolkit.get_action('package_show')(context, {'id': package_to_add_id})

                if search_results['count'] > 0:
                    return_dict['existing_resource'] = toolkit.get_action('resource_show')(context, {'id': search_results['results'][0]['id']})
                    if existing_package['private'] is False:
                        return return_dict

                # check if resource can be added to this resource

            new_resource = toolkit.get_action('resource_create')(context, {'name': 'subset_' + resource['name'], 'url': url, 'package_id': package_to_add_id, 'format': data_dict['accept'], 'subset_of': resource['id']})

            toolkit.get_action('package_relationship_create')(context, {'subject': package_to_add_id, 'object': package['id'], 'type': 'child_of'})

            return_dict['new_resource'] = new_resource
        else:
            # redirect to url if user doesn't want to create a package
            return_dict['url'] = str(url)
        return return_dict
