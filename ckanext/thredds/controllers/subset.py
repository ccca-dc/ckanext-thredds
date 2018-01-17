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
from ckan.common import _, response
import ast
import os
import mimetypes
from dateutil.relativedelta import relativedelta
from xml.etree import ElementTree
import ckanext.thredds.helpers as helpers
from ckanext.thredds.logic.action import get_ncss_subset_params

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
        package = toolkit.get_action('package_show')(context, {'id': resource['package_id']})

        try:
            variables = str(','.join([var['name'] for var in package['variables']]))
        except:
            h.flash_error('Download was not possible as the variables of the package are not defined correctly.')
            redirect(h.url_for(controller='package', action='resource_read',
                                     id=resource['package_id'], resource_id=resource['id']))

        # anonymous users are not allowed to download subset
        if authz.auth_is_anon_user(context):
            abort(401, _('Unauthorized to read resource %s') % resource_id)

        try:
            enqueue_job = toolkit.enqueue_job
        except AttributeError:
            from ckanext.rq.jobs import enqueue as enqueue_job
        enqueue_job(subset_download_job, [resource_id, variables, context['user']])

        h.flash_notice('Your subset is being created. This might take a while, you will receive an E-Mail when your subset is available')
        redirect(h.url_for(controller='package', action='resource_read',
                                 id=resource['package_id'], resource_id=resource['id']))

    def subset_get(self, resource_id):
        # TODO use real location from subset creation process
        # Check access not with resource id (can be faked)
        context = {'model': model, 'session': model.Session,
                   'user': c.user, 'auth_user_obj': c.userobj}

        try:
            rsc = get_action('resource_show')(context, {'id': resource_id})
            get_action('package_show')(context, {'id': rsc['package_id']})
        except (NotFound, NotAuthorized):
            abort(404, _('Resource not found'))

        if authz.auth_is_anon_user(context) and rsc.get('anonymous_download', 'false') == 'false':
            abort(401, _('Unauthorized to read resource %s') % rsc['name'])
        else:
            # TODO use real location 
            filepath = '/e/ckan/thredds/cache/ncss/114143850/3ea_50-3300-4796-b996-a8dfc21e2db1.nc'

            response.headers['X-Accel-Redirect'] = "/files/{0}".format(os.path.relpath(filepath, start='/e/ckan/'))
            response.headers["Content-Disposition"] = "attachment; filename={0}".format(rsc.get('url','').split('/')[-1])
            content_type, content_enc = mimetypes.guess_type(
                    rsc.get('url', ''))
            if content_type:
                response.headers['Content-Type'] = content_type
            return response


def subset_download_job(resource_id, variables, subset_user):
    context = {'model': model, 'session': model.Session,
               'user': c.user}
    resource = toolkit.get_action('resource_show')(context, {'id': resource_id})
    package = toolkit.get_action('package_show')(context, {'id': resource['package_id']})

    user = toolkit.get_action('user_show')(context, {'id':context['user']})

    # get params from metadata
    params = helpers.get_query_params(package)
    params['var'] = variables
    params['accept'] = resource['format']

    # get parent of subset
    is_part_of_id = [d for d in package['relations'] if d['relation'] == 'is_part_of']
    is_part_of_pkg = toolkit.get_action('package_show')(context, {'id': is_part_of_id[0]['id']})

    # get netcdf resource id from parent
    netcdf_resource = [res['id'] for res in is_part_of_pkg['resources'] if res['format'].lower() == 'netcdf']

    corrected_params, subset_netcdf_hash = get_ncss_subset_params(netcdf_resource[0], params, user, True, None)

    location = [corrected_params.get('location', None)]
    error = corrected_params.get('error', None)


    user = toolkit.get_action('user_show')(context, {'id':subset_user})
    _send_email(user, location, error, None, None)


def _send_email(user, location, error, new_package, existing_package):
    def _send_mail(recipient_name, recipient_email, sender_name, subject, body):
        import smtplib
        from email.mime.application import MIMEApplication
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText
        from email.utils import COMMASPACE, formatdate
        from email.header import Header
        from os.path import basename
        import paste.deploy.converters
        
        msg = MIMEMultipart()
        mail_from = config.get('smtp.mail_from')
        msg['From'] = _("%s <%s>") % (sender_name, mail_from)
        recipient = u"%s <%s>" % (recipient_name, recipient_email)
        msg['To'] = Header(recipient, 'utf-8')

        msg['Date'] = formatdate(localtime=True)
        msg['Subject'] = subject
        msg.attach(MIMEText(body.encode('utf-8'), 'plain', 'utf-8'))
    
        smtp_connection = smtplib.SMTP()
        smtp_server = config.get('smtp.server')
        smtp_starttls = paste.deploy.converters.asbool(
                    config.get('smtp.starttls'))
        smtp_user = config.get('smtp.user')
        smtp_password = config.get('smtp.password')
    
       # smtp = smtplib.SMTP(config.get('smtp.server'))
        smtp_connection.connect(smtp_server)
        try:
            #smtp_connection.set_debuglevel(True)
    
            # Identify ourselves and prompt the server for supported features.
            smtp_connection.ehlo()
    
            # If 'smtp.starttls' is on in CKAN config, try to put the SMTP
            # connection into TLS mode.
            if smtp_starttls:
                if smtp_connection.has_extn('STARTTLS'):
                    smtp_connection.starttls()
                    # Re-identify ourselves over TLS connection.
                    smtp_connection.ehlo()
                else:
                    raise MailerException("SMTP server does not support STARTTLS")
    
            # If 'smtp.user' is in CKAN config, try to login to SMTP server.
            if smtp_user:
                assert smtp_password, ("If smtp.user is configured then "
                        "smtp.password must be configured as well.")
                smtp_connection.login(smtp_user, smtp_password)
    
            smtp_connection.sendmail(mail_from, recipient_email, msg.as_string())
            #log.info("Sent email to {0}".format(send_to))
    
        except smtplib.SMTPException, e:
            msg = '%r' % e
            log.exception(msg)
            raise MailerException(msg)
        finally:
            smtp_connection.quit()

    # sending of email after successful subset creation
    if error is not None:
        body = '\nThe subset couldn\'t be created due to the following error: %s' % (error)
    else:
        body = 'Your subset is ready to download: %s' % ", ".join(location)
        if new_package is not None:
            body += '\nThe package "%s" was created' % (new_package['name'])
            if existing_package is not None:
                body += '\n You cannot set your package public as another package ("%s") has the same query and is already public.' % (existing_package['name'])
        elif existing_package is not None:
            body += '\n Your package was not created, because the package "%s" has the same query and is already public.' % (existing_package['name'])

    mail_dict = {
        'recipient_email': config.get("ckanext.contact.mail_to", config.get('email_to')),
        'recipient_name': config.get("ckanext.contact.recipient_name", config.get('ckan.site_title')),
        'subject': config.get("ckanext.contact.subject", 'Your subset is ready to download'),
        'body': body
    }

    _send_mail(user.get('display_name',''), 
               user.get('email',''),
               "CCCA Datenzentrum", 
               "Your subset is ready to download",
               body)

#    mailer.mail_recipient(
#         "Georg Seyerl", "georg.seyerl@ccca.ac.at", "Test", body)
#        config.get("ckanext.contact.recipient_name", config.get('ckan.site_title')), 
#        config.get("ckanext.contact.mail_to", config.get('email_to')), 
#        config.get("ckanext.contact.subject", 'Your subset is ready to download'), 
#        body)

