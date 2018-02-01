import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
import ckanext.thredds.logic.action as action
from ckanext.thredds import helpers


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
                'preview_enabled':True
                }

    def can_view(self, data_dict):
        resource = data_dict['resource']
        format_lower = resource.get('format', '').lower()

        if format_lower in 'netcdf':
            return True
        else:
            return False


    def view_template(self, context, data_dict):
        return 'wms_view.html'

    def setup_template_variables(self, context, data_dict):
        """Setup variables available to templates"""
        resource_id = data_dict['resource']['id']

        tpl_variables = {
            'resource_id': resource_id
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
            'get_query_params': helpers.get_query_params
            }

    # IPackageController
    def after_show(self, context, data_dict):
        # Fix for relationship problem
        data_dict.pop('relationships_as_object', None)
        data_dict.pop('relationships_as_subject', None)
