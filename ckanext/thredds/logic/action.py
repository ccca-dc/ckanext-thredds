# encoding: utf-8

import ckan.plugins.toolkit as tk
import ckan.logic
from owslib.wms import WebMapService
import os


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

    # Get Request for this controller
    req = tk.request

    # Get URL for WMS Proxy
    wms_url = 'https://sandboxdc.ccca.ac.at/thredds_proxy/wms/' + resource_id

    # WMS Object from url and extracted apikey from request header
    wms = WebMapService(wms_url, version='1.3.0',
                        headers={'Authorization':user.apikey})


    # Get Contents
    l_cont = list(wms.contents)

    # Filter Contents
    l_cont_filter = [l for l in l_cont if l not in
                     ['lat','lon','latitude','longitude','x','y']]


    d_layers = {}
    for l in l_cont_filter:
        d_layers[l] = {}
        d_layers[l]['name'] = wms.contents[l].name
        d_layers[l]['title'] = wms.contents[l].title
        d_layers[l]['abstract'] = wms.contents[l].abstract

    return d_layers


def thredds_get_capabilities(context, data_dict):
    '''Return the capabilities of a Thredds WMS resource

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
