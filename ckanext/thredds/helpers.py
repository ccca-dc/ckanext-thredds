import ckan.plugins.toolkit as tk
import ckan.lib.base as base

import ckan.model as model
import ckan.logic as logic
import ckan.lib.helpers as h
import urlparse


def get_parent_dataset(package_id):
    ctx = {'model': model}

    try:
        relationships = tk.get_action('package_relationships_list')(ctx, {'id': package_id, 'rel': 'child_of'})

        parent_id = relationships[0]['object']
        parent = tk.get_action('package_show')(ctx, {'id': parent_id})
        if parent['state'] != 'deleted':
            return parent
    except:
        return None


def get_public_children_datasets(package_id):
    ctx = {'model': model}

    children = []

    try:
        relationships = tk.get_action('package_relationships_list')(ctx, {'id': package_id, 'rel': 'parent_of'})

        for r in relationships:
            try:
                child = tk.get_action('package_show')(ctx, {'id': r['object']})
                if child['state'] == 'active':
                    children.append(child)
            except logic.NotAuthorized:
                # resources should not be returned if not authorized
                pass
    except:
        pass

    return children


def get_parent_resource(resource):
    ctx = {'model': model}

    try:
        parent_resource = tk.get_action('resource_show')(ctx, {'id': resource['subset_of']})

        return parent_resource
    except:
        return None


def check_subset_uniqueness(package_id):
    ctx = {'model': model}

    package = tk.get_action('package_show')(ctx, {'id': package_id})

    uniqueness_problems = []

    for resource in package['resources']:
        if resource.get('subset_of', '') != '':
            search_results = tk.get_action('resource_search')(ctx, {'query': "url:" + resource['url']})

            if search_results['count'] > 0:
                private_res_url = h.url_for(controller='package', action='resource_read',
                                   id=resource['package_id'], resource_id=resource['id'])
                public_res_url = h.url_for(controller='package', action='resource_read',
                                  id=search_results['results'][0]['package_id'], resource_id=search_results['results'][0]['id'])
                uniqueness_problems.append({'private_resource': private_res_url, 'public_resource': public_res_url})

    return uniqueness_problems


def get_queries_from_user(user_id):
    ctx = {'model': model}

    # CKAN 2.7. has include_private in package_search, lower versions not
    # user_packages = tk.get_action('package_search')(ctx, {'q': 'creator_user_id:"' + user_id + '"', 'include_private': 'True'})
    user_packages = tk.get_action('user_show')(ctx, {'id': user_id, 'include_datasets': 'True'})
    all_packages = tk.get_action('package_search')(ctx)

    user_queries = []

    for package in user_packages['datasets']:
        try:
            tk.get_action('package_relationships_list')(ctx, {'id': package['id'], 'rel': 'child_of'})

            for resource in package['resources']:
                if resource.get('subset_of', "") != "":
                    query = _get_params(resource)
                    if query not in user_queries:
                        user_queries.append(query)
        except:
            pass

    all_queries = []
    for package in all_packages['results']:
        if package not in user_packages['datasets']:
            try:
                tk.get_action('package_relationships_list')(ctx, {'id': package['id'], 'rel': 'child_of'})

                for resource in package['resources']:
                    if resource.get('subset_of', "") != "":
                        query = _get_params(resource)
                        if query not in all_queries:
                            all_queries.append(query)
            except:
                pass

    return user_queries, all_queries


def _get_params(resource):
    query = dict()
    query['name'] = str(resource['name'])
    query['created'] = str(resource['created'])
    parsed = urlparse.urlparse(resource['url'])
    params = urlparse.parse_qs(parsed.query)
    for param in params:
        if param == "accept":
            query['format'] = str(params[param][0])
        else:
            query[str(param)] = str(params.get(param, [""])[0])
    return query
