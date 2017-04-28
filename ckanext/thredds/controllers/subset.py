import ckan.lib.helpers as h
import ckan.lib.base as base
from urlparse import urlparse, parse_qs
from pylons import config
import ckan.plugins.toolkit as toolkit

import logging
import ckan.model as model
import ckan.logic as logic
import ckan.lib.uploader as uploader
import ckan.lib.navl.dictization_functions as dict_fns

get_action = logic.get_action
parse_params = logic.parse_params
tuplize_dict = logic.tuplize_dict
clean_dict = logic.clean_dict
check_access = logic.check_access

c = base.c
request = base.request
abort = base.abort
log = logging.getLogger(__name__)

NotAuthorized = logic.NotAuthorized


class SubsetController(base.BaseController):
    def create_subset(self):
        context = {'model': model, 'session': model.Session,
                   'user': c.user}

        # Package needs to have a organization group in the call to
        # check_access and also to save it
        try:
            check_access('package_create', context)
        except NotAuthorized:
            abort(403, _('Unauthorized to create a subset'))

        return toolkit.render('subset_create.html', {'title': 'Create Subset'})
