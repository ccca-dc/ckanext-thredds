import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
import ckanext.thredds.logic.action as action


class ThreddsPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IResourceView, inherit=True)
    plugins.implements(plugins.IRoutes, inherit=True)
    plugins.implements(plugins.IActions)

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
                'default_title': plugins.toolkit._('Thredds WMS')
                }

    def can_view(self, data_dict):
        # Returning True says a that any resource can use this view type.
        # It will appear in every resource view dropdown.
        return True


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
        return map

    # IActions
    def get_actions(self):
        actions = {'thredds_get_layers': action.thredds_get_layers,
                   'thredds_get_layerdetails': action.thredds_get_layerdetails}
        return actions
