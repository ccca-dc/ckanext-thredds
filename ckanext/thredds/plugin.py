import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
import ckanext.thredds.logic.action as action
from ckanext.thredds import helpers
import ckan.logic.validators as val
from pylons import config
import urllib
import json


class ThreddsPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IResourceView, inherit=True)
    plugins.implements(plugins.IRoutes, inherit=True)
    plugins.implements(plugins.IActions)
    plugins.implements(plugins.ITemplateHelpers)
    plugins.implements(plugins.IPackageController, inherit=True)

    # IConfigurer

    def update_config(self, config_):
        toolkit.add_template_directory(config_, 'templates')
        toolkit.add_public_directory(config_, 'public')
        toolkit.add_resource('fanstatic', 'thredds')
        #toolkit.add_resource('public', 'thredds-public')


    ## IResourceView
    def info(self):
        return {'name': 'thredds_wms_view',
                'title': plugins.toolkit._('Thredds WMS'),
                'icon': 'globe',
                'iframed': False,
                'requires_datastore': False,
                'default_title': plugins.toolkit._('View'),
                'preview_enabled':True,
                'schema': {
                    'minimum': [toolkit.get_validator('ignore_empty'), val.natural_number_validator],
                    'maximum': [toolkit.get_validator('ignore_empty'), val.natural_number_validator],
                    'num_colorbands': [toolkit.get_validator('ignore_empty'), val.is_positive_integer],
                    'logscale': [toolkit.get_validator('ignore_empty'), val.boolean_validator],
                    'default_layer': [toolkit.get_validator('ignore_empty')],
                    'default_colormap': [toolkit.get_validator('ignore_empty')]
                }
                }

    def can_view(self, data_dict):
        resource = data_dict['resource']
        format_lower = resource.get('format', '').lower()

        if 'netcdf' in format_lower:
            return True
        else:
            return False

    def view_template(self, context, data_dict):
        return 'wms_view.html'

    def form_template(self, context, data_dict):
        return 'wms_form.html'

    def setup_template_variables(self, context, data_dict):
        """Setup variables available to templates"""

        resource_id = data_dict['resource']['id']
        resource = data_dict['resource']

        #print json.dumps(data_dict,indent=4)

        #For subset
        subset_params =''
        spatial_params =''

        print "*********************Thredds"
        print resource['url']
        print resource

        # Check subset
        if '/subset/' in resource['url']:

            #Get original resource id
            package = data_dict['package']
            is_part_of_id = [d for d in package['relations'] if d['relation'] == 'is_part_of']

            if is_part_of_id:
                    try:
                        variables = str(','.join([var['name'] for var in package['variables']]))
                    except:
                        h.flash_error('Thredds View was not possible as the variables of the package are not defined correctly.')
                        redirect(h.url_for(controller='package', action='resource_read',
                                                 id=resource['package_id'], resource_id=resource['id']))
                    is_part_of_pkg = toolkit.get_action('package_show')(context, {'id': is_part_of_id[0]['id']})

                    # get netcdf resource id from parent
                    netcdf_resource = [res['id'] for res in is_part_of_pkg['resources'] if 'netcdf' in res['format'].lower()]

                    if netcdf_resource:
                        resource_id = netcdf_resource[0]
                        subset_params = helpers.get_query_params(package)
                        spatial_params = package['spatial']
                    else:
                        subset_params ={}
                        subset_params['var'] = variables
                        spatial_params = package['spatial']
                        #params['accept'] = res['format']

                    #ckan_url = config.get('ckan.site_url', '')
                    ##thredds_location = config.get('ckanext.thredds.location')
                    #url = ('%s/%s/ncss/%s?%s' % (ckan_url, thredds_location, netcdf_resource[0], urllib.urlencode(params)))

        tpl_variables = {
            'resource_id': resource_id,
            'subset_params' : subset_params,
            'spatial_params' : spatial_params,
            'minimum': data_dict['resource_view'].get('minimum', ''),
            'maximum': data_dict['resource_view'].get('maximum', ''),
            'num_colorbands': data_dict['resource_view'].get('num_colorbands', ''),
            'logscale': data_dict['resource_view'].get('logscale', ''),
            'default_layer': data_dict['resource_view'].get('default_layer', ''),
            'default_colormap': data_dict['resource_view'].get('default_colormap', '')
        }

        return tpl_variables

    # IRoutes
    def before_map(self, map):
        # image upload
        map.connect('tds_proxy', '/tds_proxy/{service}/{res_id}',
                    controller='ckanext.thredds.controllers.proxy:ThreddsProxyController',
                    action='tds_proxy')
        map.connect('tds_proxy', '/tds_proxy/{service}/{res_id}/{extra}',
                    controller='ckanext.thredds.controllers.proxy:ThreddsProxyController',
                    action='tds_proxy')
        map.connect('subset_create', '/subset/{resource_id}/create',
                    controller='ckanext.thredds.controllers.subset:SubsetController',
                    action='subset_create')
        map.connect('subset_download', '/subset/{resource_id}/download',
                    controller='ckanext.thredds.controllers.subset:SubsetController',
                    action='subset_download')
        map.connect('subset_get', '/subset/{resource_id}/get/{location}/{file_type}',
                    controller='ckanext.thredds.controllers.subset:SubsetController',
                    action='subset_get')
        return map

    # IActions
    def get_actions(self):
        actions = {'thredds_get_layers': action.thredds_get_layers,
                   'thredds_get_layerdetails': action.thredds_get_layerdetails,
                   'subset_create': action.subset_create,
                   'thredds_get_metadata_info': action.thredds_get_metadata_info}
        return actions

    # ITemplateHelpers
    def get_helpers(self):
        return {
            'get_parent_dataset': helpers.get_parent_dataset,
            'get_public_children_datasets': helpers.get_public_children_datasets,
            'check_subset_uniqueness': helpers.check_subset_uniqueness,
            'get_queries_from_user': helpers.get_queries_from_user,
            'get_query_params': helpers.get_query_params,
            'check_if_res_can_create_subset': helpers.check_if_res_can_create_subset,
            'get_current_datetime': helpers.get_current_datetime
            }

    # IPackageController
    def after_show(self, context, data_dict):
        # Fix for relationship problem
        data_dict.pop('relationships_as_object', None)
        data_dict.pop('relationships_as_subject', None)
