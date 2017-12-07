# encoding: utf-8

import ckan.plugins.toolkit as tk
import ckan.logic
from owslib.wms import WebMapService
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
import ckan.lib.base as base
from pylons import config
import datetime
import ckan.plugins as p
import socket
import ckan.lib.mailer as mailer
import time
import ckan.model as model
from xml.etree import ElementTree
import ckanext.thredds.helpers as helpers
import ckanext.resourceversions.helpers
import copy

check_access = logic.check_access

_get_or_bust = logic.get_or_bust

abort = base.abort

NotAuthorized = logic.NotAuthorized
NotFound = logic.NotFound
Invalid = df.Invalid
ValidationError = logic.ValidationError

c = base.c


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
    :param format: format of the subset (NetCDF, XML or CSV)
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

    metadata = toolkit.get_action('thredds_get_metadata_info')(context, {'id': id})

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
            if northf > float(metadata['coordinates']['north']) and southf > float(metadata['coordinates']['north']):
                errors['north'] = [u'coordinate is further north than bounding box of resource']
                errors['south'] = [u'coordinate is further north than bounding box of resource']
            elif northf < float(metadata['coordinates']['south']) and southf < float(metadata['coordinates']['south']):
                errors['north'] = [u'coordinate is further south than bounding box of resource']
                errors['south'] = [u'coordinate is further south than bounding box of resource']
            else:
                if northf > float(metadata['coordinates']['north']):
                    data_dict['north'] = metadata['coordinates']['north']
                if southf < float(metadata['coordinates']['south']):
                    data_dict['south'] = metadata['coordinates']['south']
        else:
            if northf > float(metadata['coordinates']['north']):
                errors['north'] = [u'latitude is further north than bounding box of resource']
            if northf < float(metadata['coordinates']['south']):
                errors['north'] = [u'latitude is further south than bounding box of resource']

    if eastWestOk is True:
        eastf = float(data_dict['east'])
        if data_dict.get('west', "") != "":
            westf = float(data_dict['west'])
            if eastf > float(metadata['coordinates']['east']) and westf > float(metadata['coordinates']['east']):
                errors['east'] = [u'coordinate is further east than bounding box of resource']
                errors['west'] = [u'coordinate is further east than bounding box of resource']
            elif eastf < float(metadata['coordinates']['west']) and westf < float(metadata['coordinates']['west']):
                errors['east'] = [u'coordinate is further west than bounding box of resource']
                errors['west'] = [u'coordinate is further west than bounding box of resource']
            else:
                if eastf > float(metadata['coordinates']['east']):
                    data_dict['east'] = metadata['coordinates']['east']
                if westf < float(metadata['coordinates']['west']):
                    data_dict['west'] = metadata['coordinates']['west']
        else:
            if eastf > float(metadata['coordinates']['east']):
                errors['east'] = [u'longitude is further east than bounding box of resource']
            if eastf < float(metadata['coordinates']['west']):
                errors['east'] = [u'longitude is further west than bounding box of resource']

    # error resource creation section
    if data_dict.get('type', 'download').lower() == "create_resource":
        if data_dict.get('resource_name', "") == '':
            errors['resource_name'] = [u'Missing Value']
        if data_dict.get('title', "") == '':
            errors['title'] = [u'Missing Value']
        if data_dict.get('name', "") == '':
            errors['name'] = [u'Missing Value']
        else:
            model = context['model']
            session = context['session']
            result = session.query(model.Package).filter(model.Package.name.like(data_dict['name']+ "-v%")).first()

            if result:
                errors['name'] = [u'That URL is already in use.']
            elif len(data_dict['name']) < PACKAGE_NAME_MIN_LENGTH:
                errors['name'] = [u'URL is shorter than minimum (' + str(PACKAGE_NAME_MIN_LENGTH) + u')']
            elif len(data_dict['name']) > PACKAGE_NAME_MAX_LENGTH:
                errors['name'] = [u'URL is longer than maximum (' + str(PACKAGE_NAME_MAX_LENGTH) + u')']
        if data_dict.get('organization', "") == '':
            errors['organization'] = [u'Missing Value']
        else:
            toolkit.get_action('organization_show')(context, {'id': data_dict['organization']})
    else:
        # error format section
        if data_dict.get('format', "") != "":
            if data_dict['point'] is True and data_dict['format'].lower() not in {'netcdf', 'csv', 'xml'}:
                errors['format'] = [u'Wrong format']
            elif data_dict['point'] is False and data_dict['format'].lower() != 'netcdf':
                errors['format'] = [u'Wrong format']
        else:
            errors['format'] = [u'Missing value']

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
            else:
                if given_end > package_end:
                    data_dict['time_end'] = str(package_end)
                if given_start < package_start:
                    data_dict['time_start'] = str(package_start)
    elif data_dict.get('time_start', "") != "" and data_dict.get('time_end', "") == "":
        errors['time_end'] = [u'Missing value']
    elif data_dict.get('time_start', "") == "" and data_dict.get('time_end', "") != "":
        errors['time_start'] = [u'Missing value']

    # error layer section
    if data_dict.get('layers', "") != "":
        if type(data_dict['layers']) is list:
            for l in data_dict['layers']:
                if not any(var['name'] == l for var in metadata['variables']):
                    errors['layers'] = [u'layer "' + l + '" does not exist']
        else:
            if not any(var['name'] == data_dict['layers'] for var in metadata['variables']):
                errors['layers'] = [u'layer "' + data_dict['layers'] + '" does not exist']
    else:
        errors['layers'] = [u'Missing value']

    # end of error section
    if len(errors) > 0:
        raise ValidationError(errors)
    else:
        try:
            enqueue_job = toolkit.enqueue_job
        except AttributeError:
            from ckanext.rq.jobs import enqueue as enqueue_job
        enqueue_job(subset_create_job, [c.user, resource, data_dict, times_exist, metadata])
    return "Your subset is being created. This might take a while, you will receive an E-Mail when your subset is available."


def subset_create_job(user, resource, data_dict, times_exist, metadata):
    context = {'model': model, 'session': model.Session,
               'user': user}

    user = toolkit.get_action('user_show')(context, {'id': user})

    # start building URL params with var (required)
    if type(data_dict['layers']) is list:
        params = {'var': ','.join(data_dict['layers'])}
    else:
        params = {'var': data_dict['layers']}

    # adding format
    if data_dict.get('format', ''):
        params['accept'] = data_dict['format'].lower()

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

    only_location = False
    if data_dict.get('type', 'download').lower() == "download":
        only_location = True
    corrected_params, subset_hash = get_ncss_subset_params(resource['id'], params, only_location, metadata)

    return_dict = dict()

    # create resource if requested from user
    if data_dict.get('type', 'download').lower() == "create_resource" and "error" not in corrected_params:
        package = toolkit.get_action('package_show')(context, {'id': resource['package_id']})

        # is this check necessary?
        # try:
        #     check_access('package_show', context, {'id': package['id']})
        # except NotAuthorized:
        #     abort(403, _('Unauthorized to show package'))

        # check if url already exists
        if subset_hash is not None:
            search_results = toolkit.get_action('package_search')(context, {'rows': 10000, 'fq':
                            'res_hash:%s' % (subset_hash)})

            if search_results['count'] > 0:
                return_dict['existing_package'] = search_results['results'][0]

        if 'existing_package' not in return_dict or data_dict.get('private', 'True').lower() == 'true':
            # check if private is True or False otherwise set private to True
            if 'private' not in data_dict or data_dict['private'].lower() not in {'true', 'false'}:
                data_dict['private'] = 'True'

            # creating new package from the current one with few changes
            new_package = package.copy()
            new_package.update(corrected_params)
            new_package.pop('id')
            new_package.pop('resources')
            new_package.pop('groups')
            new_package.pop('revision_id')

            new_package['iso_mdDate'] = new_package['metadata_created'] = new_package['metadata_modified'] = datetime.datetime.now()
            new_package['owner_org'] = data_dict['organization']
            new_package['name'] = data_dict['name']
            new_package['title'] = data_dict['title']
            new_package['private'] = data_dict['private']

            new_package['relations'] = [{'relation': 'is_part_of', 'id': package['id']}]

            # add subset creator
            subset_creator = dict()
            subset_creator['name'] = user['display_name']
            subset_creator['email'] = user['email']
            subset_creator['role'] = "subset creator"
            new_package['contact_points'].append(subset_creator)

            if subset_hash is not None:
                new_package['hash'] = subset_hash

            # need to pop package otherwise it overwrites the current pkg
            context.pop('package')

            new_package = toolkit.get_action('package_create')(context, new_package)

            # add resource in all formats
            subset_formats = ['NetCDF']
            if data_dict['point'] is True:
                subset_formats.extend(['xml', 'csv'])

            for subset_format in subset_formats:
                new_resource = {'name': data_dict['resource_name'], 'url': 'subset', 'format': subset_format, 'subset_of': resource['id'], 'anonymous_download': 'False'}
                new_resource['package_id'] = new_package['id']
                new_resource = toolkit.get_action('resource_create')(context, new_resource)

                # url needs id of the resource
                # TODO ckan_url in both methods
                ckan_url = config.get('ckan.site_url', '')
                new_resource['url'] = ('%s/subset/%s/download' % (ckan_url, new_resource['id']))
                context['create_version'] = False
                new_resource = toolkit.get_action('resource_update')(context, new_resource)

            return_dict['new_package'] = new_package

    location = corrected_params['location']
    error = corrected_params.get('error', None)
    new_package = return_dict.get('new_package', None)
    existing_package = return_dict.get('existing_package', None)

    send_email(location, error, new_package, existing_package)


def send_email(location, error, new_package, existing_package):
    # sending of email after successful subset creation
    if error is not None:
        body = '\nThe subset couldn\'t be created due to the following error: %s' % (error)
    else:
        body = 'Your subset is ready to download: ' + location
        if new_package is not None:
            body += '\nThe package "%s" was created' % (new_package['name'])
            if existing_package is not None:
                body += '\n You cannot set your package public as another package ("%s") has the same query and is already public.' % (existing_package['name'])
        elif existing_package is not None:
            body += '\n Your package was not created, because the package "%s" has the same query and is already public.' % (existing_package['name'])

    mail_dict = {
        'recipient_email': config.get("ckanext.contact.mail_to", config.get('email_to')),
        'recipient_name': config.get("ckanext.contact.recipient_name", config.get('ckan.site_title')),
        'subject': config.get("ckanext.contact.subject", 'Your subset is ready to download'),
        'body': body
    }
    print(body)
    #
    # # Allow other plugins to modify the mail_dict
    # for plugin in p.PluginImplementations(IContact):
    #     plugin.mail_alter(mail_dict, data_dict)

    # try:
    #     mailer.mail_recipient(**mail_dict)
    # except (mailer.MailerException, socket.error):
    #     h.flash_error(_(u'Sorry, there was an error sending the email. Please try again later'))


def get_ncss_subset_params(resource_id, params, only_location, orig_metadata):
    params['response_file'] = "false"
    headers={'Authorization': user.apikey}

    ckan_url = config.get('ckan.site_url', '')
    thredds_location = config.get('ckanext.thredds.location')

    r = requests.get('http://sandboxdc.ccca.ac.at/' + thredds_location + '/ncss/88d350e9-5e91-4922-8d8c-8857553d5d2f', params=params, headers=headers)
    # r = requests.get(ckan_url + '/' + thredds_location + '/ncss/' + resource['id'], params=params, headers=headers)
    print(r.url)

    corrected_params = dict()
    subset_hash = None

    if r.status_code == 200:
        # TODO not working for point
        tree = ElementTree.fromstring(r.content)

        corrected_params['location'] = tree.get('location')

        # TODO add if not local
        # import hashlib
        # hasher = hashlib.md5()
        #
        # with open(location, 'rb') as f:
        #     for chunk in iter(lambda: f.read(128*hasher.block_size), b''):
        #         hasher.update(chunk)
        # subset_hash = hasher.hexdigest()
        # print(subset_hash)

        if not only_location:
            # add spatial to new resource
            lat_lon_box = tree.find('LatLonBox')
            n = lat_lon_box.find('north').text
            e = lat_lon_box.find('east').text
            s = lat_lon_box.find('south').text
            w = lat_lon_box.find('west').text
            corrected_params['spatial'] = helpers.coordinates_to_spatial(n, e, s, w)

            # add time to new resource
            time_span = tree.find('TimeSpan')
            corrected_params['temporal_start'] = h.date_str_to_datetime(time_span.find('begin').text[:-1])

            if time_span.find('begin').text != time_span.find('end').text:
                corrected_params['temporal_end'] = h.date_str_to_datetime(time_span.find('end').text[:-1])
            else:
                corrected_params['temporal_end'] = None

            # add variables to new resource
            # variables must be changed to dict
            corrected_params['variables'] = []
            layers = params['var'].split(",")
            for layer in layers:
                corrected_params['variables'].append((item for item in orig_metadata['variables'] if item["name"] == layer).next())

            corrected_params['dimensions'] = orig_metadata['dimensions']
    else:
        corrected_params['error'] = r.content

    return corrected_params, subset_hash


def _change_list_of_dicts_for_search(list_of_dicts):
    for index, t in enumerate(list_of_dicts):
        new_dict = dict([(str(k), v) for k, v in t.items()])
        for k, val in new_dict.items():
            if val is None:
                new_dict[k] = "null"
            elif isinstance(val, unicode):
                new_dict[k] = str(val)
            elif type(val) is list:
                list_elements = []
                for list_element in val:
                    list_elements.append(str(list_element))
                new_dict[k] = list_elements
        t.update(new_dict)
        list_of_dicts[index] = dict([(str(k), v) for k, v in t.items()])
    return list_of_dicts


@ckan.logic.side_effect_free
def thredds_get_metadata_info(context, data_dict):

    # Resource ID
    model = context['model']
    user = context['auth_user_obj']

    metadata = dict()

    resource_id = tk.get_or_bust(data_dict, 'id')

    ckan_url = config.get('ckan.site_url', '')
    thredds_location = config.get('ckanext.thredds.location')

    try:
        # headers={'Authorization': user.apikey}
    except:
        raise NotAuthorized

    # NCML section
    ncml_url = '/'.join([ckan_url, thredds_location, 'ncml', resource_id])

    try:
        # r = requests.get(ncml_url, headers=headers)
        r = requests.get('http://sandboxdc.ccca.ac.at/' + 'tds_proxy/ncml/' + '/88d350e9-5e91-4922-8d8c-8857553d5d2f', headers=headers)
    except Exception as e:
        raise NotFound("Thredds Server can not provide layer details")

    ncml_tree = ElementTree.fromstring(r.content)

    # get description and references
    metadata['notes'] = ncml_tree.find(".//*[@name='comment']").attrib["value"]
    metadata['references'] = ncml_tree.find(".//*[@name='references']").attrib["value"]

    # NCSS section
    ncss_url = '/'.join([ckan_url, thredds_location, 'ncss', resource_id, 'dataset.xml'])

    try:
        # r = requests.get(ncss_url, headers=headers)
        r = requests.get('http://sandboxdc.ccca.ac.at/' + 'tds_proxy/ncss/88d350e9-5e91-4922-8d8c-8857553d5d2f/dataset.xml', headers=headers)
    except Exception as e:
        raise NotFound("Thredds Server can not provide layer details")

    ncss_tree = ElementTree.fromstring(r.content)

    # get coordinates
    lat_lon_box = ncss_tree.find('LatLonBox')
    n = lat_lon_box.find('north').text
    e = lat_lon_box.find('east').text
    s = lat_lon_box.find('south').text
    w = lat_lon_box.find('west').text
    metadata['spatial'] = helpers.coordinates_to_spatial(n, e, s, w)
    metadata['coordinates'] = {'north': n, 'east': e, 'south': s, 'west': w}

    # get time
    time_span = ncss_tree.find('TimeSpan')

    metadata['temporal_start'] = time_span.find('begin').text
    if metadata['temporal_start'] != time_span.find('end').text:
        metadata['temporal_end'] = time_span.find('end').text
    else:
        metadata['temporal_end'] = None

    # get dimensions
    metadata['dimensions'] = []
    dimensions = ncss_tree.findall('axis')
    for dimension in dimensions:
        d = dict()
        d['name'] = dimension.attrib["name"]
        d['units'] = dimension.find(".attribute/[@name='units']").attrib["value"]
        d['description'] = dimension.find(".attribute/[@name='long_name']").attrib["value"]
        d['start'] = dimension.find("values").attrib["start"]
        d['shape'] = dimension.attrib["shape"]
        d['increment'] = dimension.find("values").attrib["increment"]

        metadata['dimensions'].append(d)

    # get variables
    metadata['variables'] = []
    grids = ncss_tree.findall(".//grid")
    for grid in grids:
        axis_type = grid.find(".attribute/[@name='_CoordinateAxisType']")
        if axis_type is None:
            g = dict()
            g['name'] = grid.attrib['name']
            g['description'] = grid.attrib['desc']
            g['standard_name'] = grid.find(".attribute/[@name='standard_name']").attrib["value"]
            g['units'] = grid.find(".attribute/[@name='units']").attrib["value"]
            g['shape'] = grid.attrib['shape'].split(" ")

            metadata['variables'].append(g)

    return metadata

    # time information should be used for error and display section in subset_create
