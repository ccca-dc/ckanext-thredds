import ckan.lib.helpers as h
import ckan.lib.base as base
from urlparse import urlparse, parse_qs
from pylons import config
import ckan.plugins.toolkit as toolkit

import logging
import ckan.model as model
from ckan.model import (PACKAGE_NAME_MIN_LENGTH, PACKAGE_NAME_MAX_LENGTH)
import ckan.logic as logic
import ckan.lib.uploader as uploader
import ckan.lib.navl.dictization_functions as dict_fns
import ckan.authz as authz
import ckan.lib.navl.dictization_functions as df
from ckan.common import _
import ast
from dateutil.relativedelta import relativedelta

get_action = logic.get_action
parse_params = logic.parse_params
tuplize_dict = logic.tuplize_dict
clean_dict = logic.clean_dict
check_access = logic.check_access

c = base.c
request = base.request
abort = base.abort
redirect = base.redirect
log = logging.getLogger(__name__)

NotAuthorized = logic.NotAuthorized
NotFound = logic.NotFound
Invalid = df.Invalid
ValidationError = logic.ValidationError

unflatten = df.unflatten


class SubsetController(base.BaseController):

    def create_subset(self, resource_id):

        """
        Return a contact form
        :return: html
        """

        data = {}
        errors = {}
        error_summary = {}

        context = {'model': model, 'session': model.Session,
                   'user': c.user}

        # check if user can perform a resource_show
        try:
            check_access('resource_show', context, {'id': resource_id})
        except NotAuthorized:
            abort(403, _('Unauthorized to show resource'))
        except NotFound:
            abort(404, _('The resource {id} could not be found.'
                         ).format(id=resource_id))

        # check if user can download resource
        #if authz.auth_is_anon_user(context) and resource.get('anonymous_download', 'false') == 'false':
        if authz.auth_is_anon_user(context):
            abort(401, _('Unauthorized to create subset of %s') % resource_id)

        resource = toolkit.get_action('resource_show')(context, {'id': resource_id})
        package = toolkit.get_action('package_show')(context, {'id': resource['package_id']})

        # Submit the data
        if 'save' in request.params:
            # values are just returned in case of error(s)
            data, errors, error_summary = self._submit(context, resource, package)
        else:
            data['all_layers'] = []

            try:
                layers = toolkit.get_action('thredds_get_layers')(context, {'id': resource['id']})
                layer_details = toolkit.get_action('thredds_get_layerdetails')(context, {'id': resource['id'], 'layer': layers[0]['children'][0]['id']})
            except Exception:
                h.flash_error("This resource cannot create a subset")
                redirect(h.url_for(controller='package', action='resource_read',
                                   id=package['id'], resource_id=resource['id']))

            data['bbox'] = layer_details['bbox']

            for layer in layers[0]['children']:
                data['all_layers'].append({'id': layer['id'], 'label': layer['label']})

        # check if user is allowed to create package
        data['create_pkg'] = True
        try:
            check_access('package_create', context)
        except NotAuthorized:
            data['create_pkg'] = False

        data['pkg'] = package

        data['organizations'] = []
        for org in toolkit.get_action('organization_list_for_user')(context, {'permission': 'create_dataset'}):
            data['organizations'].append({'value': org['id'], 'text': org['display_name']})

        data['relationships'] = []

        try:
            relationships = toolkit.get_action('package_relationships_list')(context, {'id': package['id'], 'rel': 'parent_of'})
        except:
            relationships = []

        for rel in relationships:
            try:
                child = toolkit.get_action('package_show')(context, {'id': rel['object']})
                if child['state'] != 'deleted':
                        check_access('resource_update', context, {'id': child['id']})
                        data['relationships'].append(child)
            except NotAuthorized:
                pass

        vars = {'data': data, 'errors': errors, 'error_summary': error_summary}
        return toolkit.render('subset_create.html', extra_vars=vars)

    @staticmethod
    def _submit(context, resource, package):
        data = logic.clean_dict(unflatten(logic.tuplize_dict(logic.parse_params(request.params))))

        data['bbox'] = [n[2:-1] for n in data['bbox'].replace('[', '').replace(']', '').split(", ")]
        data['all_layers'] = ast.literal_eval(str(data['all_layers']))
        data['id'] = resource['id']

        errors = {}
        error_summary = {}

        try:
            data = toolkit.get_action('subset_create')(context, data)
            if 'new_resource' in data:
                if 'existing_resource' in data:
                    public_res_url = h.url_for(controller='package', action='resource_read',
                                       id=data['existing_resource']['package_id'], resource_id=data['existing_resource']['id'])
                    h.flash_notice('This dataset cannot be set public, because another <strong><a href="' + public_res_url + '" class="alert-link">subset</a></strong> with this query is already public.', allow_html=True)

                redirect(h.url_for(controller='package', action='resource_read',
                                    id=data['new_resource']['package_id'], resource_id=data['new_resource']['id']))
            elif 'new_resource' not in data and 'existing_resource' in data:
                h.flash_notice('This subset already exists. Please use this subset for citation.')
                redirect(h.url_for(controller='package', action='resource_read',
                                    id=data['existing_resource']['package_id'], resource_id=data['existing_resource']['id']))
            elif 'url' in data:
                h.redirect_to(data['url'])
        except ValidationError, e:
            errors = e.error_dict
            error_summary = e.error_summary

        return data, errors, error_summary
