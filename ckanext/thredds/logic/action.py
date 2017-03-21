# encoding: utf-8

import ckan.plugins.toolkit as tk
from owslib.wms import WebMapService
import os


def thredds_get_layers(context, data_dict):
    '''Return the layers of a resource from Thredds WMS.
    Exclude lat, lon, latitude, longitude, x, y

    :param id: the id of the resource
    :type id: string
    :rtype: list
    '''
    # Resource ID
    model = context['model']
    user = context['user']

    resource_id = tk.get_or_bust(data_dict,'id')

    # Get Request for this controller
    req = tk.request

    # Get URL for WMS Proxy
    wms_url = 'https://sandboxdc.ccca.ac.at/wms_proxy/' + resource_id

    # WMS Object from url and extracted apikey from request header
    wms = WebMapService(wms_url, version='1.3.0',
                        headers={'Authorization': req.headers['Authorization']})

    # Get Contents
    l_cont = list(wms.contents)

    # Filter Contents
    l_cont_filter = [l for l in l_cont if l not in
                     ['lat','lon','latitude','longitude','x','y']]


    d_layers = {}
    for l in l_cont_filter:
        d_layers[l] = {}
        d_layers[l]['name'] = wms.contens[l].name
        d_layers[l]['title'] = wms.contens[l].title
        d_layers[l]['abstract'] = wms.contens[l].abstract

    return d_layers


def thredds_get_dimensions(context, data_dict):
    '''Return the dimensions of a Thredds WMS resource layer.

    :param id: the id of the resource
    :type id: string
    :param layer: the layer name for the requested resources
    :type layer: string
    :rtype: dictionary
    '''
    # wms['layer'].dimensions
    pass


def thredds_get_time(context, data_dict):
    '''Return the temporal extent of the resources layer

    :param id: the id or name of the resource
    :type id: string
    :param layer: the layer name for the requested resources
    :type layer: string
    :rtype: list
    '''
    # wms['layer'].dimensions
    pass


def thredds_get_spatial(context, data_dict):
    '''Return the spatial extent of the resources layer

    :param id: the id or name of the resource
    :type id: string
    :param layer: the layer name for the requested resources
    :type layer: string
    :rtype: list
    '''
    # wms['layer'].dimensions
    pass
