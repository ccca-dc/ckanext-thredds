import ckan
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
from xml.etree import ElementTree
import requests
import ast
import ckanext.thredds.helpers as helpers

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

    def subset_create(self, resource_id):

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
            # get metadata from nclm and ncss
            data['metadata'] = toolkit.get_action('thredds_get_metadata_info')(context, {'id': resource_id})

        # check if user is allowed to create package
        data['create_pkg'] = True
        try:
            check_access('package_create', context)
        except NotAuthorized:
            data['create_pkg'] = False

        data['pkg'] = package
        data['res_name'] = resource['name']

        data['organizations'] = []
        for org in toolkit.get_action('organization_list_for_user')(context, {'permission': 'create_dataset'}):
            data['organizations'].append({'value': org['id'], 'text': org['display_name']})

        vars = {'data': data, 'errors': errors, 'error_summary': error_summary}
        return toolkit.render('subset_create.html', extra_vars=vars)

    @staticmethod
    def _submit(context, resource, package):
        data = logic.clean_dict(unflatten(logic.tuplize_dict(logic.parse_params(request.params))))

        data['id'] = resource['id']
        data['metadata'] = ast.literal_eval(data['metadata'])

        errors = {}
        error_summary = {}

        try:
            message = toolkit.get_action('subset_create')(context, data)

            h.flash_notice(message)
            redirect(h.url_for(controller='package', action='resource_read',
                                     id=package['id'], resource_id=resource['id']))
        except ValidationError, e:
            errors = e.error_dict
            error_summary = e.error_summary

        return data, errors, error_summary

    def subset_download(self, resource_id):
        context = {'model': model, 'session': model.Session,
                   'user': c.user}

        resource = toolkit.get_action('resource_show')(context, {'id': resource_id})

        # anonymous users are not allowed to download subset
        if authz.auth_is_anon_user(context):
            abort(401, _('Unauthorized to read resource %s') % resource_id)

        try:
            enqueue_job = toolkit.enqueue_job
        except AttributeError:
            from ckanext.rq.jobs import enqueue as enqueue_job
        enqueue_job(subset_download_job, [resource_id])

        h.flash_notice('Your subset is being created. This might take a while, you will receive an E-Mail when your subset is available')
        redirect(h.url_for(controller='package', action='resource_read',
                                 id=resource['package_id'], resource_id=resource['id']))


def subset_download_job(resource_id):
    context = {'model': model, 'session': model.Session,
               'user': c.user}
    resource = toolkit.get_action('resource_show')(context, {'id': resource_id})
    package = toolkit.get_action('package_show')(context, {'id': resource['package_id']})

    # get params from metadata
    params = dict()
    params['var'] = 'rsds'
    # add variables
    # params['var'] = ','.join([var['name'] for var in package['variables']])
    # add coordinates to params
    if package.get('spatial', '') != '':
        params.update(helpers.spatial_to_coordinates(package['spatial']))
    # params['time_start'] = resource['temporals'][0]['start_date']
    # params['time_ends'] = resource['temporals'][0]['end_date']

    ckan_url = config.get('ckan.site_url', '')
    thredds_location = config.get('ckanext.thredds.location')

    params['response_file'] = "false"
    headers = {"Authorization": ""}
    # headers={'Authorization': user.apikey}
    # ncss_url = '/'.join([ckan_url, thredds_location, 'ncss', resource['subset_of'])

    r = requests.get('http://sandboxdc.ccca.ac.at/tds_proxy/ncss/88d350e9-5e91-4922-8d8c-8857553d5d2f', params=params, headers=headers)
    # r = requests.get(ncss_url, params=params, headers=headers)
    print(r.url)
    tree = ElementTree.fromstring(r.content)
    location = tree.get('location')

    body = 'Your subset is ready to download: ' + location

    mail_dict = {
        'recipient_email': config.get("ckanext.contact.mail_to", config.get('email_to')),
        'recipient_name': config.get("ckanext.contact.recipient_name", config.get('ckan.site_title')),
        'subject': config.get("ckanext.contact.subject", 'Your subset is ready to download'),
        'body': body
    }

    print(body)

    # try:
    #     mailer.mail_recipient(**mail_dict)
    # except (mailer.MailerException, socket.error):
    #     h.flash_error(_(u'Sorry, there was an error sending the email. Please try again later'))
