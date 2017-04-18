# encoding: utf-8

import ckan.plugins.toolkit as tk
import ckan.logic
from owslib.wms import WebMapService
import os
import requests
import json


@ckan.logic.side_effect_free
def thredds_get_layers(context, data_dict):
    '''Return the layers of a resource from Thredds WMS.
    Exclude lat, lon, latitude, longitude, x, y

    :param id: the id of the resource
    :type id: string
    :rtype: list
    '''
    # Resource ID
    model = context['model']
    user = context['auth_user_obj']

    resource_id = tk.get_or_bust(data_dict,'id')

    # Get URL for WMS Proxy
    wms_url = 'https://sandboxdc.ccca.ac.at/tds_proxy/wms/' + resource_id
    
    # Headers and payload for thredds request
    headers={'Authorization':user.apikey}

    payload={'item':'menu',
             'request':'GetMetadata'}

    # Thredds request
    r = requests.get(wms_url, params=payload, headers=headers)
    layer_tds = json.loads(r.content)
    
    # Filter Contents
    layers_filter = []
    for idx,childa in enumerate(layer_tds['children']):
        layers_filter.append(dict())
        layers_filter[idx]['label'] = childa.get('label','')
        layers_filter[idx]['children'] = ([el for el in childa['children'] if el['id'] not in
                                   ['lat','lon','latitude','longitude','x','y']])


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
    wms_url = 'https://sandboxdc.ccca.ac.at/tds_proxy/wms/' + resource_id
    
    headers={'Authorization':user.apikey}

    payload={'item':'layerDetails',
             'layerName':layer_name,
             'request':'GetMetadata'}

    # WMS Object from url and extracted apikey from request header
    r = requests.get(wms_url, params=payload, headers=headers)
    layer_details = json.loads(r.content)
    try:
        del layer_details['datesWithData']
    except:
        pass
    
    return layer_details
