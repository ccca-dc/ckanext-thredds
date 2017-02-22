import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit


class ThreddsPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IResourceView, inherit=True)

    # IConfigurer

    def update_config(self, config_):
        toolkit.add_template_directory(config_, 'templates')
        toolkit.add_public_directory(config_, 'public')
        toolkit.add_resource('fanstatic', 'thredds')


    ## IResourceView
    def info(self):
        return {'name': 'thredds_wms_view',
                'title': plugins.toolkit._('Thredds WMS'),
                'icon': 'pencil',
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

    # def setup_template_variables(self, context, data_dict):
    #     """Setup variables available to templates"""
    #     pass

