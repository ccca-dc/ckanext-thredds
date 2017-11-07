import ckan.plugins.toolkit as tk
import ckan.lib.base as base

import ckan.model as model
import ckan.logic as logic
import ckan.lib.helpers as h
import urlparse
import json


def get_public_children_datasets(package_id):
    ctx = {'model': model}
    d = {'relation': 'is_part_of', 'id': package_id}
    d = dict((k.decode('utf8'), v.decode('utf8')) for k, v in d.items())
    # add include_private to newer CKAN version
    search_results = tk.get_action('package_search')(ctx, {'fq': "relations:*%s*" % (json.dumps(str(d)))})
    return search_results['results']


def get_parent_dataset(package_id):
    ctx = {'model': model}

    package = tk.get_action('package_show')(ctx, {'id': package_id})

    try:
        parent_id = [element['id'] for element in package['relations'] if element['relation'] == 'is_part_of']
        parent_package = tk.get_action('package_show')(ctx, {'id': parent_id})
        return parent_package
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
    all_packages = tk.get_action('package_search')(ctx, {'rows': '10000'})

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
        # private check only necessary in older CKAN versions
        if package not in user_packages['datasets'] and package['private'] is False:
            try:
                # lower CKAN versions have a problem with package_relationships_list
                # if the user does not have an own dataset
                if len(user_packages['datasets']) > 0:
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
    # don't call it just name, otherwise problem in template
    query['query_name'] = str(resource['name'])
    query['created'] = str(resource['created'])
    parsed = urlparse.urlparse(resource['url'])
    params = urlparse.parse_qs(parsed.query)
    for param in params:
        if param == "accept":
            query['format'] = str(params[param][0])
        else:
            query[str(param)] = str(params.get(param, [""])[0])
    return query


def coordinates_to_spatial(north, east, south, west):
    n = float(north)
    e = float(east)
    s = float(south)
    w = float(west)
    coordinates = [[w, s], [e, s], [e, n], [w, n], [w, s]]
    return ('{"type": "MultiPolygon", "coordinates": [[' + str(coordinates) + ']]}')


def spatial_to_coordinates(spatial):
    spatial = json.loads(spatial)

    coordinates = dict()
    coordinates['north'] = spatial['coordinates'][0][0][2][1]
    coordinates['east'] = spatial['coordinates'][0][0][1][0]
    coordinates['south'] = spatial['coordinates'][0][0][0][1]
    coordinates['west'] = spatial['coordinates'][0][0][0][0]

    return coordinates
