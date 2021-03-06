# encoding: utf-8

import ckan.plugins.toolkit as tk
import ckan.logic
from owslib.wms import WebMapService
import requests
import json
import ckan.lib.helpers as h
import ckan.logic as logic
from ckan.model import (PACKAGE_NAME_MIN_LENGTH, PACKAGE_NAME_MAX_LENGTH)
from dateutil.relativedelta import relativedelta
from ckan.common import _
import ckan.lib.navl.dictization_functions as df
import ckan.lib.base as base
from pylons import config
import datetime
import ckan.plugins as p
import ckan.lib.mailer as mailer
import ckan.model as model
from xml.etree import ElementTree
import ckanext.thredds.helpers as helpers
import ckanext.resourceversions.helpers

#from ckanext.contact.interfaces import IContact #makes problems and obviously we do not need it? Anja, 15.2.18
import socket
import hashlib
import os

import logging
log = logging.getLogger(__name__)


check_access = logic.check_access

_get_or_bust = logic.get_or_bust

abort = base.abort

NotAuthorized = logic.NotAuthorized
NotFound = logic.NotFound
Invalid = df.Invalid
ValidationError = logic.ValidationError

c = base.c


@ckan.logic.side_effect_free
def thredds_get_minmax(context, data_dict):
    '''Return the min/max values of a layer or vertical level (elevation)
      from Thredds WMS.

    :param id: the id of the resource
    :param: layer
    :param: elevation (optional)
    :returns: list
    '''

    # Resource ID
    model = context['model']
    user = context['auth_user_obj']

    resource_id = tk.get_or_bust(data_dict,'id')
    resource = tk.get_action('resource_show')(context, {'id': resource_id})

    #check if the resource is a subset
    if '/subset/' in resource['url']:

        package = tk.get_action('package_show')(context, {'id': resource['package_id']})

        # get params from metadata
        try:
            variables = str(','.join([var['name'] for var in package['variables']]))
        except:
            h.flash_error('Thredds View was not possible as the variables of the package are not defined correctly.')
            redirect(h.url_for(controller='package', action='resource_read',
                                     id=resource['package_id'], resource_id=resource['id']))
        params = helpers.get_query_params(package)
        params['var'] = variables
        params['item']='minmax'
        params['request']= 'GetMetadata'
        payload = params
        #print params
        # Get Resource_id from parent
        # get parent of subset
        is_part_of_id = [d for d in package['relations'] if d['relation'] == 'is_part_of']
        is_part_of_pkg = tk.get_action('package_show')(context, {'id': is_part_of_id[0]['id']})

        # get netcdf resource id from parent
        netcdf_resource = [res['id'] for res in is_part_of_pkg['resources'] if  'netcdf' in res['format'].lower()]
        resource_id = netcdf_resource[0]
    else:
        payload={'item':'minmax',
                'request':'GetMetadata'}

    layers = tk.get_or_bust(data_dict,'layers')
    elevation = tk.get_or_bust(data_dict,'elevation')

    if layers:
        payload['layers'] = layers
    if elevation:
        payload['elevation'] = elevation

    #FIXME: Check subset and st the parameter right!!!
    payload= data_dict
    payload['item'] ='minmax'
    payload['request'] ='GetMetadata'
    payload.pop('id')
    # Get URL for WMS Proxy
    ckan_url = config.get('ckan.site_url', '')
    wms_url = ckan_url + '/thredds/wms/ckan/' + "/".join([resource_id[0:3],resource_id[3:6],resource_id[6:]])


    # Headers and payload for thredds request
    try:
        headers={'Authorization':user.apikey}
    except:
        raise NotAuthorized

    # Thredds request
    try:
        r = requests.get(wms_url, params=payload, headers=headers)
        minmax = json.loads(r.content)

    except Exception as e:
        print "***************** Errror"
        raise NotFound("Thredds Server can not provide layer information for the resource")

    if 'min' in minmax:
        if float(minmax['min']) > 1:
            minmax['min'] = round(minmax['min'], 2)
    if 'max' in minmax:
        if float(minmax['max']) > 1:
         minmax['max'] = round(minmax['max'], 2)

    return minmax


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
    resource = tk.get_action('resource_show')(context, {'id': resource_id})

    #check if the resource is a subset

    if '/subset/' in resource['url']:

        package = tk.get_action('package_show')(context, {'id': resource['package_id']})

        # get params from metadata
        try:
            variables = str(','.join([var['name'] for var in package['variables']]))
        except:
            h.flash_error('Thredds View was not possible as the variables of the package are not defined correctly.')
            redirect(h.url_for(controller='package', action='resource_read',
                                     id=resource['package_id'], resource_id=resource['id']))
        params = helpers.get_query_params(package)
        params['var'] = variables
        params['accept'] = resource['format']
        params['item']='menu'
        params['request']= 'GetMetadata'
        payload = params
        #print params
        # Get Resource_id from parent
        # get parent of subset
        is_part_of_id = [d for d in package['relations'] if d['relation'] == 'is_part_of']
        is_part_of_pkg = tk.get_action('package_show')(context, {'id': is_part_of_id[0]['id']})

        # get netcdf resource id from parent
        netcdf_resource = [res['id'] for res in is_part_of_pkg['resources'] if  'netcdf' in res['format'].lower()]
        resource_id = netcdf_resource[0]
    else:

        payload={'item':'menu',
                 'request':'GetMetadata'}

    # Get URL for WMS Proxy
    ckan_url = config.get('ckan.site_url', '')
    wms_url = ckan_url + '/thredds/wms/ckan/' + "/".join([resource_id[0:3],resource_id[3:6],resource_id[6:]])

    # Headers and payload for thredds request
    try:
        headers={'Authorization':user.apikey}
    except:
        raise NotAuthorized


    # Thredds request
    try:
        r = requests.get(wms_url, params=payload, headers=headers)
        layer_tds = json.loads(r.content)

    except Exception as e:
        #print "***************** Errror"
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
    user = context['auth_user_obj']

    resource_id = tk.get_or_bust(data_dict,'id')
    layer_name = tk.get_or_bust(data_dict,'layer')

    resource = tk.get_action('resource_show')(context, {'id': resource_id})

    if '/subset/' in resource['url']:
        # get params from metadata
        package = tk.get_action('package_show')(context, {'id': resource['package_id']})
        try:
            variables = str(','.join([var['name'] for var in package['variables']]))
        except:
            h.flash_error('Thredds View was not possible as the variables of the package are not defined correctly.')
            redirect(h.url_for(controller='package', action='resource_read',
                                     id=resource['package_id'], resource_id=resource['id']))
        params = helpers.get_query_params(package)
        params['var'] = variables
        params['accept'] = resource['format']
        params['item']='layerDetails'
        params['layerName']=layer_name
        params['request']= 'GetMetadata'
        payload = params
        #print params
        # Get Resource_id from parent
        # get parent of subset
        is_part_of_id = [d for d in package['relations'] if d['relation'] == 'is_part_of']
        is_part_of_pkg = tk.get_action('package_show')(context, {'id': is_part_of_id[0]['id']})

        # get netcdf resource id from parent
        netcdf_resource = [res['id'] for res in is_part_of_pkg['resources'] if 'netcdf' in res['format'].lower()]
        resource_id = netcdf_resource[0]

    else:
        payload={'item':'layerDetails',
                 'layerName':layer_name,
                 'request':'GetMetadata'}

    # Get URL for WMS Proxy
    ckan_url = config.get('ckan.site_url', '')
    wms_url = ckan_url + '/thredds/wms/ckan/' + "/".join([resource_id[0:3],resource_id[3:6],resource_id[6:]])

    try:
        headers={'Authorization':user.apikey}
    except:
        raise NotAuthorized

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
    _param vertical_level: Vertical level - currently only *Pressure* supported
    :rtype: dictionary
    '''
    errors = {}

    id = _get_or_bust(data_dict, 'id')
    resource = tk.get_action('resource_show')(context, {'id': id})
    package = tk.get_action('package_show')(context, {'id': resource['package_id']})

    metadata = tk.get_action('thredds_get_metadata_info')(context, {'id': id})

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
        if data_dict.get('package_title', "") == '':
            errors['package_title'] = [u'Missing Value']
        if data_dict.get('package_name', "") == '':
            errors['package_name'] = [u'Missing Value']
        else:
            model = context['model']
            session = context['session']
            result = session.query(model.Package).filter(model.Package.name.like(data_dict['package_name']+ "-v%")).first()

            if result:
                errors['package_name'] = [u'That URL is already in use.']
            elif len(data_dict['package_name']) < PACKAGE_NAME_MIN_LENGTH:
                errors['package_name'] = [u'URL is shorter than minimum (' + str(PACKAGE_NAME_MIN_LENGTH) + u')']
            elif len(data_dict['package_name']) > PACKAGE_NAME_MAX_LENGTH:
                errors['package_name'] = [u'URL is longer than maximum (' + str(PACKAGE_NAME_MAX_LENGTH) + u')']
        if data_dict.get('organization', "") == '':
            errors['organization'] = [u'Missing Value']
        else:
            tk.get_action('organization_show')(context, {'id': data_dict['organization']})
    else:
        # error format section ??? TODO Kathi -- why just for download???
        if data_dict.get('format', "") != "":
            if data_dict['point'] is True and data_dict['format'].lower() not in {'netcdf', 'csv', 'xml','netcdf4'}:
                errors['format'] = [u'Wrong format']
            elif data_dict['point'] is False and data_dict['format'].lower() not in {'netcdf', 'netcdf4'}:
                errors['format'] = [u'Wrong format']
        else:
            errors['format'] = [u'Missing value']

    # Anja, 20.7.18 - check netcdf 3 or 4 (no long / long)
    # 23.7.28 AND remove 'type' field again
    # Would lead to change in subsets fields and
    # prevent update - subset_read_only_field

    vars = metadata['variables']
    dims = metadata['dimensions']

    for d in dims:
        if d['type'] in ['long', 'int64']:
            data_dict['format'] ='netcdf4'
        d.pop('type')

    for v in vars:
        if v['type'] in ['long', 'int64']:
            data_dict['format'] ='netcdf4'
        v.pop('type')

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
            enqueue_job = tk.enqueue_job
        except AttributeError:
            from ckanext.rq.jobs import enqueue as enqueue_job
        enqueue_job(subset_create_job, [c.user, resource, data_dict, times_exist, metadata])
    return "Your subset is being created. This might take a while, you will receive an E-Mail when your subset is available."


def subset_create_job(user, resource, data_dict, times_exist, metadata):
    '''The subset creation job (jobs are always executed as default user)

    :param user: the user name or id
    :type user: string
    :param resource: the resource of which a subset is to be created
    :type resource: dict
    :param data_dict: all informations regarding the new subset
    :type data_dict: dict
    :param times_exist: TODO
    :type times_exist: boolean
    :param metadata: the thredds metadata for the parent resource
    :type metadata: string
    '''
    context = {'model': model, 'session': model.Session,
               'user': user}

    user = tk.get_action('user_show')(context, {'id': user})

    #Anja, 17.7.18: Do we have a vertical_level?
    vertical_included = False

    # start building URL params with var (required)
    if type(data_dict['layers']) is list:
        params = {'var': ','.join(data_dict['layers'])}
    else:
        params = {'var': data_dict['layers']}

    # adding format # Anja, check for netcdf3/4
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

    # check vertical level: Anja, 2.7.2018
    if 'vertical_level' in data_dict and data_dict.get('vertical_level', "") != "" and data_dict.get('vertical_level', "").lower() != "all":
        #print "LEVEL******************++"
        #print data_dict.get('vertical_level', "")
        params['vertCoord'] = float(data_dict['vertical_level'])
        vertical_included = True

    only_location = False
    if data_dict.get('type', 'download').lower() == "download":
        only_location = True
    corrected_params, resource_params = get_ncss_subset_params(resource['id'], params, user, only_location, metadata)

    return_dict = dict()

    location = None

    if "error" not in corrected_params:
        location = [corrected_params['location']]

        # create resource if requested from user
        if data_dict.get('type', 'download').lower() == "create_resource":
            package = tk.get_action('package_show')(context, {'id': resource['package_id']})

            # check if url already exists
            if resource_params is not None and resource_params.get('hash', None) is not None:
                search_results = tk.get_action('package_search')(context, {'rows': 10000, 'fq':
                                'res_hash:%s' % (resource_params['hash']), 'include_versions': True})

                if search_results['count'] > 0:
                    return_dict['existing_package'] = search_results['results'][0]

            if 'existing_package' not in return_dict or str(data_dict.get('private', 'True')).lower() == 'true':
                # check if private is True or False otherwise set private to True
                if 'private' not in data_dict or str(data_dict['private']).lower() not in {'true', 'false'}:
                    data_dict['private'] = 'True'

                # creating new package from the current one with few changes
                new_package = package.copy()
                new_package.update(corrected_params)
                new_package.pop('id')
                new_package.pop('resources')
                new_package.pop('groups')
                new_package.pop('revision_id')
                new_package.pop('uri', None)

                new_package['created'] = new_package['metadata_created'] = new_package['metadata_modified'] = datetime.datetime.now()
                new_package['owner_org'] = data_dict['organization']
                new_package['name'] = data_dict['package_name']
                new_package['title'] = data_dict['package_title']
                new_package['private'] = data_dict['private']
                new_package['spatial_name'] = data_dict.get('spatial_name', '')

                if params.get('north', "") != "":
                    new_package['spatial'] = helpers.coordinates_to_spatial(params['north'], params['east'], params['south'], params['west'])

                new_package['relations'] = [{'relation': 'is_part_of', 'id': package['id']}]

                # add subset creator
                subset_creator = dict()
                subset_creator['name'] = user['display_name']
                subset_creator['email'] = user['email']
                subset_creator['role'] = "subset creator"
                if 'contact_points' not in new_package:
                    new_package['contact_points'] = []
                new_package['contact_points'].append(subset_creator)

                #Anja, 17.7.18: Check vertical level
                if len(new_package['dimensions']) >3:
                    for i, dim in enumerate(new_package['dimensions']):
                        if dim['name'].lower()==  "pressure":
                            #Anja, 23.7.18
                            # Do not save values because we dont have a corresponding field in Editor
                            #dim['values'] =[data_dict['vertical_level']]
                            if 'values' in dim:
                                new_package['dimensions'][i].pop('values')
                            if vertical_included:
                                dim['start'] = data_dict['vertical_level']
                                dim['shape'] = '1' # Through this we store and identify the vertical level

                # need to pop package otherwise it overwrites the current pkg
                context.pop('package')

                new_package = tk.get_action('package_create')(context, new_package)

                # add resource in all formats
                subset_formats = ['NetCDF']
                if data_dict['point'] is True:
                    subset_formats.extend(['xml', 'csv'])

                for subset_format in subset_formats:
                    new_resource = {'name': data_dict['resource_name'], 'url': 'subset', 'format': subset_format, 'anonymous_download': 'False', 'package_id': new_package['id']}
                    if subset_format.lower() == 'netcdf':
                        if resource_params is not None:
                            new_resource['hash'] = resource_params.get('hash', None)
                        if resource_params is not None:
                            new_resource['size'] = resource_params.get('size', None)
                        #Anja, 20.7.18: check for netcdf4
                        if data_dict['format'] == 'netcdf4':
                            params['accept'] = 'netcdf4'
                            new_resource['format_version'] = '4'
                    else:
                        params['accept'] = subset_format
                        corrected_params_new_res, resource_params_new_res = get_ncss_subset_params(resource['id'], params, user, True, metadata)

                        if "error" not in corrected_params_new_res:
                            location.append(corrected_params_new_res['location'])

                            if resource_params_new_res is not None:
                                new_resource['hash'] = resource_params_new_res.get('hash',None)
                            if resource_params_new_res is not None:
                                new_resource['size'] = resource_params_new_res.get('size',None)

                    new_resource = tk.get_action('resource_create')(context, new_resource)

                    # url needs id of the resource
                    # TODO ckan_url in both methods
                    ckan_url = config.get('ckan.site_url', '')
                    new_resource['url'] = ('%s/subset/%s/download' % (ckan_url, new_resource['id']))
                    context['create_version'] = False
                    new_resource = tk.get_action('resource_update')(context, new_resource)

                    #Anja, 11.7.18, create view of Netcdf
                    if 'netcdf' in subset_format.lower():
                        try:
                            view_found = False
                            rvl = tk.get_action('resource_view_list') (context, {'id':res['id']})
                            if rvl:
                                for x in rvl:
                                    if x['view_type'] == 'thredds_wms_view':
                                        view_found = True

                            if not view_found:
                                res = tk.get_action('resource_view_create')(context,
                                        {'resource_id':new_resource['id'],
                                         'view_type': 'thredds_wms_view',
                                         'title':'View',
                                         'description':'',
                                         'default_layer':'0',
                                          'default_level':'0',
                                          'logscale': False}
                                          )
                        except:
                            print "-----ERROR: Subset Create - Error Creating View"
                            continue

                return_dict['new_package'] = new_package

    error = corrected_params.get('error', None)
    new_package = return_dict.get('new_package', None)
    existing_package = return_dict.get('existing_package', None)

    # Resource ID from parent
    send_email(resource['id'], user, location[0], error, new_package, existing_package)


def send_email(res_id, user, location, error, new_package, existing_package):
    '''Send the subset response email

    :param res_id: the id of the parent resource
    :type res_id: string
    :param user: the user name or id
    :type user: string
    :param location: the resource of which a subset is to be created
    :type location: dict
    :param new_package: metadata the new subset package
    :type new_package: dict
    :param existing_package: metadata of the existing subset package
    :type existing_package: dict
    '''

    # If location is present, only take two last elements
    if location:
        #location = location.split('/',2)[2:][0]
        file_path = location.split('/')[-2]
        file_type = location.split('/')[-1].split('.')[-1]

    # sending of email after successful subset creation
    if error is not None:
        body = '\nThe subset couldn\'t be created due to the following error: %s' % (error)
    else:
        body = 'Your subset is ready to download: %s' % "/".join([config.get('ckan.site_url'), 'subset', res_id, 'get', file_path, file_type])
        if new_package is not None:
            body += '\nThe package "%s" was created and is available at: %s' % (new_package['title'], config.get('ckan.site_url') + h.url_for(controller='package', action='read', id=new_package['name']))
            if existing_package is not None:
                body += '\n You cannot set your package public as another package ("%s") has the same query and is already public.' % (existing_package['name'])
        elif existing_package is not None:
            body += '\n Your package was not created, because the package "%s" has the same query and is already public.' % (existing_package['name'])

    # mail_dict = {
    #     'recipient_email': user.get('display_name',''),
    #     'recipient_name': user.get('email',''),
    #     'subject': 'Your subset is ready to download',
    #     'body': body
    # }

    _send_mail(
        user.get('display_name',''),
        user.get('email',''),
        'CCCA Datenzentrum',
        'Your subset is ready to download',
         body
    )

    # # Allow other plugins to modify the mail_dict
    # for plugin in p.PluginImplementations(IContact):
    #     plugin.mail_alter(mail_dict, data_dict)

    # try:
    #     mailer.mail_recipient(**mail_dict)
    # except (mailer.MailerException, socket.error):
    #     h.flash_error(_(u'Sorry, there was an error sending the email. Please try again later'))

def _send_mail(recipient_name, recipient_email, sender_name, subject, body):
    import smtplib
    from email.mime.application import MIMEApplication
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from email.utils import COMMASPACE, formatdate
    from email.header import Header
    from os.path import basename
    import paste.deploy.converters

    msg = MIMEMultipart()
    mail_from = config.get('smtp.mail_from')
    msg['From'] = _("%s <%s>") % (sender_name, mail_from)
    recipient = u"%s <%s>" % (recipient_name, recipient_email)
    msg['To'] = Header(recipient, 'utf-8')

    msg['Date'] = formatdate(localtime=True)
    msg['Subject'] = subject
    msg.attach(MIMEText(body.encode('utf-8'), 'plain', 'utf-8'))

    smtp_connection = smtplib.SMTP()
    smtp_server = config.get('smtp.server')
    smtp_starttls = paste.deploy.converters.asbool(
                config.get('smtp.starttls'))
    smtp_user = config.get('smtp.user')
    smtp_password = config.get('smtp.password')

   # smtp = smtplib.SMTP(config.get('smtp.server'))
    smtp_connection.connect(smtp_server)
    try:
        #smtp_connection.set_debuglevel(True)

        # Identify ourselves and prompt the server for supported features.
        smtp_connection.ehlo()

        # If 'smtp.starttls' is on in CKAN config, try to put the SMTP
        # connection into TLS mode.
        if smtp_starttls:
            if smtp_connection.has_extn('STARTTLS'):
                smtp_connection.starttls()
                # Re-identify ourselves over TLS connection.
                smtp_connection.ehlo()
            else:
                raise mailer.MailerException("SMTP server does not support STARTTLS")

        # If 'smtp.user' is in CKAN config, try to login to SMTP server.
        if smtp_user:
            assert smtp_password, ("If smtp.user is configured then "
                    "smtp.password must be configured as well.")
            smtp_connection.login(smtp_user, smtp_password)

        smtp_connection.sendmail(mail_from, recipient_email, msg.as_string())
        #log.info("Sent email to {0}".format(send_to))

    except smtplib.SMTPException as e:
        msg = '%r' % e
        raise mailer.MailerException(msg)
    finally:
        smtp_connection.quit()


def get_ncss_subset_params(res_id, params, user, only_location, orig_metadata):
    '''Get the ncss subset parameters

    :param res_id: the id of the parent resource
    :type res_id: string
    :param params: TODO
    :type params: dict
    :param user: the users name or id
    :type user: string
    :param only_location: TODO
    :type only_location: dict
    :param orig_metadata:TODO
    :type orig_metadata: dict
    :rtype: dict, dict
    '''
    params['response_file'] = "false"
    headers={'Authorization': user.get('apikey')}

    ckan_url = config.get('ckan.site_url', '')
    thredds_location = config.get('ckanext.thredds.location')

    r = requests.get('/'.join([ckan_url, thredds_location, 'ncss', 'ckan', res_id[0:3], res_id[3:6], res_id[6:]]), params=params, headers=headers)

    corrected_params = dict()
    resource_params = None

    if r.status_code == 500:  # Oks 31 Problem may be with status code 500 or 200 (see below)
        #Check time dimension
        if 'Illegal base time' in r.content and 'Value 31' in r.content:
            #try again with 30
            zeit = params['time_start']

            if zeit.find('31'):
                params['time_start'] = zeit.replace('31','30')

            zeit = params['time_end']

            if zeit.find('31'):
                params['time_end'] = zeit.replace('31','30')

            r = requests.get('/'.join([ckan_url, thredds_location, 'ncss', 'ckan', res_id[0:3], res_id[3:6], res_id[6:]]), params=params, headers=headers)
            if r.status_code != 200:
                print "****************** ERROR 31: Create subset: something regarding the time did not work (31):"
                print r.content
                corrected_params['error'] = r.content
                return corrected_params, resource_params

    if r.status_code == 200:

        #Check netcdf3, Anja 4.7.2018
        if 'illegal dataType' in r.content and 'netcdf-3' in r.content:
            #try again with netcdf4
            params['accept']='netcdf4'
            r = requests.get('/'.join([ckan_url, thredds_location, 'ncss', 'ckan', res_id[0:3], res_id[3:6], res_id[6:]]), params=params, headers=headers)
            if r.status_code != 200:
                print "****************** ERROR: Create subset: something did not work:"
                print r.content
                corrected_params['error'] = r.content
                return corrected_params, resource_params

        #Check time dimension
        if 'Illegal base time' in r.content and 'Value 31' in r.content:
            #try again with 30
            zeit = params['time_start']

            if zeit.find('31'):
                params['time_start'] = zeit.replace('31','30')

            zeit = params['time_end']

            if zeit.find('31'):
                params['time_end'] = zeit.replace('31','30')

            r = requests.get('/'.join([ckan_url, thredds_location, 'ncss', 'ckan', res_id[0:3], res_id[3:6], res_id[6:]]), params=params, headers=headers)
            if r.status_code != 200:
                print "****************** ERROR: Create subset: something regarding the time did not work:"
                print r.content
                corrected_params['error'] = r.content
                return corrected_params, resource_params

        if 'HDF error' in r.content:
            print "***************** ERROR: Create subset: something else did not work (HDF Error):"
            print r.content
            corrected_params['error'] = r.content
            return corrected_params, resource_params


        # TODO not working for point
        tree = ElementTree.fromstring(r.content)

        corrected_params['location'] = tree.get('location')

        #Anja, 28.3.18 - > needs tds ncss path ....
        storage_path = config.get('ckanext.thredds.ncss_cache')

        # Hashsum
        file_path = os.path.join(storage_path, corrected_params['location'])
        hasher = hashlib.md5()

        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(128*hasher.block_size), b''):
                hasher.update(chunk)

        resource_params = dict()
        resource_params['hash'] = hasher.hexdigest()

        # Filesize
        resource_params['size'] = os.path.getsize(file_path)

        if not only_location:
            # removed for cases with spatial query as ncss always returns different coordinates
            # add spatial to new resource
            if params.get('north', "") == "":
                lat_lon_box = tree.find('LatLonBox')
                n = lat_lon_box.find('north').text
                e = lat_lon_box.find('east').text
                s = lat_lon_box.find('south').text
                w = lat_lon_box.find('west').text
                corrected_params['spatial'] = helpers.coordinates_to_spatial(n, e, s, w)

            # add time to new resource
            time_span = tree.find('TimeSpan')
            if time_span != None and time_span != '':
                corrected_params['temporal_start'] = h.date_str_to_datetime(time_span.find('begin').text[:-1])

                if time_span.find('begin').text != time_span.find('end').text:
                    corrected_params['temporal_end'] = h.date_str_to_datetime(time_span.find('end').text[:-1])
                else:
                    corrected_params['temporal_end'] = None
            else:
                # Anja 15.6.2018
                # Attention: We might have time information in the package but NOT in the resource!
                # Delete it! TODO: Better would be to check in wms_view.js wether the resource really has time information
                # Especially important for climate change signals
                corrected_params['temporal_end'] = ''
                corrected_params['temporal_start'] = ''


            # add variables to new resource
            # variables must be changed to dict
            corrected_params['variables'] = []
            layers = params['var'].split(",")
            for layer in layers:
                corrected_params['variables'].append((item for item in orig_metadata['variables'] if item["name"] == layer).next())

            corrected_params['dimensions'] = orig_metadata['dimensions']
    else:
        corrected_params['error'] = r.content

    return corrected_params, resource_params


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
    """Extract the metadata from a file with thredds capabilities.
       This only works for cf conformal netcdf files.

    :param id: The id of the resource
    :type id: string
    :returns: dict with available metadata from resource
    """
    # Resource ID
    user = context.get('auth_user_obj', None)

    metadata = dict()

    resource_id = tk.get_or_bust(data_dict, 'id')

    ckan_url = config.get('ckan.site_url', '')
    thredds_location = config.get('ckanext.thredds.location')

    try:
        if user is not None:
            headers = {'Authorization': user.apikey}
        else:
            user = tk.get_action('user_show')(context, {'id': context['user']})
            headers = {'Authorization': user['apikey']}
    except:
        raise NotAuthorized

    # Extract NCML metadata
    ncml_url = '/'.join([ckan_url, thredds_location, 'ncml', 'ckan', resource_id[0:3], resource_id[3:6], resource_id[6:]])
    try:
        r = requests.get(ncml_url, headers=headers)
    except Exception as e:
        raise NotFound("Thredds Server can not provide layer details")

    if r.status_code == 200:
        ncml_tree = ElementTree.fromstring(r.content)
        _parse_ncml_metadata_info(ncml_tree, metadata)

        # Extract NCSS metadata
        ncss_url = '/'.join([ckan_url, thredds_location, 'ncss', 'ckan', resource_id[0:3],resource_id[3:6],resource_id[6:], 'dataset.xml'])
        try:
            r = requests.get(ncss_url, headers=headers)
        except Exception as e:
            raise NotFound("Thredds Server can not provide layer details")

        if r.status_code == 200:
            ncss_tree = ElementTree.fromstring(r.content)
            _parse_ncss_metadata_info(ncss_tree, metadata)

    return metadata

    # time information should be used for error and display section in subset_create


def _parse_ncml_metadata_info(ncml_tree, md_dict):
    # get description and references
    if ncml_tree.find(".//*[@name='comment']") is not None:
        md_dict['notes'] = ncml_tree.find(".//*[@name='comment']").attrib["value"]
    if ncml_tree.find(".//*[@name='references']") is not None:
        md_dict['references'] = ncml_tree.find(".//*[@name='references']").attrib["value"]

def _parse_ncss_metadata_info(ncss_tree, md_dict):
    # NCSS section
    # get coordinates
    lat_lon_box = ncss_tree.find('LatLonBox')
    n = lat_lon_box.find('north').text
    e = lat_lon_box.find('east').text
    s = lat_lon_box.find('south').text
    w = lat_lon_box.find('west').text
    md_dict['spatial'] = helpers.coordinates_to_spatial(n, e, s, w)
    md_dict['coordinates'] = {'north': n, 'east': e, 'south': s, 'west': w}

    # get time
    time_span = ncss_tree.find('TimeSpan')
    if time_span != None and time_span != '': # Anja 28.6.2018 - ckan advised not to use: "if time_span:"
        md_dict['temporal_start'] = time_span.find('begin').text
        if md_dict['temporal_start'] != time_span.find('end').text:
            md_dict['temporal_end'] = time_span.find('end').text
        else:
            md_dict['temporal_end'] = None

    # get dimensions
    md_dict['dimensions'] = []
    dimensions = ncss_tree.findall('axis')
    for dimension in dimensions:
        d = dict()
        d['name'] = dimension.attrib["name"]
        d['units'] = dimension.find(".attribute/[@name='units']").attrib["value"]
        d['description'] = dimension.find(".attribute/[@name='long_name']").attrib["value"]
        d['shape'] = dimension.attrib["shape"] #'shape' means number of values

        #check for type - netcdf 3 or 4 (if long included)
        try:
            d['type'] = dimension.attrib["type"]
        except:
            d['type'] = ''

        # not all dimensions contain start and increment attributes
        try:
            d['start'] = dimension.find("values").attrib["start"]
        except:
            d['start'] = ''
        try:
            d['increment'] = dimension.find("values").attrib["increment"]
        except:
            d['increment'] = ''

        # Check for Pressure, Anja, 2.7.18 - so far not general and abstract possible
        # because sometimes 'start' and 'increment' are empty and all definitions are in 'units'

        if d['name'].lower() == 'pressure':
            str_values =[]
            str_values = dimension.find("values").text.split(" ")
            values = [float(x) for x in str_values]
            d['values'] = values
            d['start'] = values[0]
            d['increment'] = 'discrete values' #Anja, 18.7.2018

        md_dict['dimensions'].append(d)

    # get variables
    md_dict['variables'] = []
    grids = ncss_tree.findall(".//grid")
    for grid in grids:
         # if axis_type in grid this is not a variable!
        axis_type = grid.find(".attribute/[@name='_CoordinateAxisType']")
        if axis_type is None:
            g = dict()
            g['name'] = grid.attrib['name']
            g['description'] = grid.attrib['desc']
            if grid.find(".attribute/[@name='standard_name']") is not None:
                g['standard_name'] = grid.find(".attribute/[@name='standard_name']").attrib["value"]
            if grid.find(".attribute/[@name='units']") is not None:
                g['units'] = grid.find(".attribute/[@name='units']").attrib["value"]
            g['shape'] = grid.attrib['shape'].split(" ")
            #check for type - netcdf 3 or 4 (if long included)
            try:
                g['type'] = grid.attrib["type"]
            except:
                g['type'] = ''
            md_dict['variables'].append(g)
