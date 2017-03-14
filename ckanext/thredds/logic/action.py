# encoding: utf-8

from owslib.wms import WebMapService

import ckan.logic
import ckan.plugins.toolkit as tk

import os

ValidationError = ckan.logic.ValidationError
NotFound = ckan.logic.NotFound
_check_access = ckan.logic.check_access
_get_or_bust = ckan.logic.get_or_bust
_get_action = ckan.logic.get_action


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

    resource_id = tk.get_action('get_or_bust')(data_dict,'id')

    # Get URL for WMS Proxy
    wms_url = tk.url_for('wms_proxy', id=resource_id)

    # WMS Object
    wms = WebMapService(wms_url, version='1.3.0',
                        headers={'Authorization':user.apikey})

    # Get Contents
    l_cont = list(wms.contents)

    # Filter Contents
    l_cont_filter = [l for l in l_cont if l not in
                     ['lat','lon','latitude','longitude','x','y']]

    return l_cont_filter


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
    '''Return the metadata of a dataset (package) and its resources.

    :param id: the id or name of the dataset
    :type id: string
    :param use_default_schema: use default package schema instead of
        a custom schema defined with an IDatasetForm plugin (default: False)
    :type use_default_schema: bool
    :param include_tracking: add tracking information to dataset and
        resources (default: False)
    :type include_tracking: bool
    :rtype: dictionary

    '''
    # wms['layer'].dimensions
    pass


def thredds_get_spatial(context, data_dict):
    '''Return the metadata of a dataset (package) and its resources.

    :param id: the id or name of the dataset
    :type id: string
    :param use_default_schema: use default package schema instead of
        a custom schema defined with an IDatasetForm plugin (default: False)
    :type use_default_schema: bool
    :param include_tracking: add tracking information to dataset and
        resources (default: False)
    :type include_tracking: bool
    :rtype: dictionary

    '''
    # wms['layer'].dimensions
    pass
