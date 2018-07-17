import ckan.plugins.toolkit as tk
import ckan.lib.base as base

import ckan.model as model
import ckan.logic as logic
import ckan.lib.helpers as h
import json

from ckan.common import _, ungettext, g, c, request, session


def get_public_children_datasets(package_id):
    ctx = {'model': model}
    rel = {'relation': 'is_part_of', 'id': str(package_id)}
    # add include_private to newer CKAN version
    search_results = tk.get_action('package_search')(ctx, {'rows': 10000, 'fq': "extras_relations:%s" % (json.dumps('%s' % rel)), 'include_versions': True})
    return search_results['results']


def get_parent_dataset(package_id):
    ctx = {'model': model, 'ignore_auth': True}

    package = tk.get_action('package_show')(ctx, {'id': package_id})

    try:
        parent_ids = [element['id'] for element in package['relations'] if element['relation'] == 'is_part_of']
        if len(parent_ids) > 0:
            parent_package = tk.get_action('package_show')(ctx, {'id': parent_ids[0]})
            return parent_package
        return None
    except:
        return None


def check_subset_uniqueness(package_id):
    ctx = {'model': model}

    package = tk.get_action('package_show')(ctx, {'id': package_id})

    uniqueness_problems = []

    for resource in package['resources']:
        if resource.get('hash', '') != '':
            search_results = tk.get_action('package_search')(ctx, {'rows': 10000, 'fq':
                                'res_hash:%s' % (resource['hash']), 'include_versions': True})

            if search_results['count'] > 0:
                public_package = h.url_for(controller='package', action='read',
                                  id=search_results['results'][0]['name'])
                uniqueness_problems.append(public_package)

    return uniqueness_problems


def get_queries_from_user(user_id):
    ctx = {'model': model}

    # CKAN 2.7. has include_private in package_search, lower versions not
    # user_packages = tk.get_action('package_search')(ctx, {'q': 'creator_user_id:"' + user_id + '"', 'include_private': 'True'})
    user_packages = tk.get_action('user_show')(ctx, {'id': user_id, 'include_datasets': 'True'})
    all_packages = tk.get_action('package_search')(ctx, {'rows': 10000, 'fq': "relations:*%s*" % ('is_part_of')})

    user_queries = []

    for package in user_packages['datasets']:
        if 'relations' in package and type(package['relations']) == list and len(package['relations']) > 0 and type(package['relations'][0]) == dict:
            children = [package for element in package['relations'] if element['relation'] == 'is_part_of']

            if len(children) > 0:
                query = get_query_params(package)
                query['query_name'] = str(package['name'])
                query['created'] = str(package['metadata_created'])

                if query not in user_queries:
                    user_queries.append(query)

    all_queries = []
    for package in all_packages['results']:
        # private check only necessary in older CKAN versions
        if package['private'] is False and package not in user_packages['datasets']:
            try:
                query = get_query_params(package)
                query['query_name'] = str(package['name'])
                query['created'] = str(package['metadata_created'])

                if query not in all_queries:
                    all_queries.append(query)
            except:
                pass

    #print(all_queries)
    return user_queries, all_queries


def get_query_params(package):
    # get query params from metadata
    query = dict()
    # add coordinates to params
    if package.get('spatial', '') != '':
        query.update(spatial_to_coordinates(package['spatial']))

    query['time_start'] = str(package.get('temporal_start', ''))
    query['time_end'] = str(package.get('temporal_end', ''))
    if query['time_end'] == '':
        query['time_end'] = str(query['time_start'])

    #Anja, 17.7.18: Check vertical level
    if len(package['dimensions']) > 3:
        for dim in package['dimensions']:
            if dim['name'].lower()==  "pressure":
                if dim['shape'] == 1: # We have only one vertical level selected
                    query['vertCoord'] = dim['start']

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
    lon_list = [item[1] for item in spatial['coordinates'][0][0]]
    coordinates['south'] = min(float(l) for l in lon_list)
    coordinates['north'] = max(float(l) for l in lon_list)

    lat_list = [item[0] for item in spatial['coordinates'][0][0]]
    coordinates['west'] = min(float(l) for l in lat_list)
    coordinates['east'] = max(float(l) for l in lat_list)

    return coordinates


def check_if_res_can_create_subset(resource_id):
    context = {'model': model,
               'user': c.user}
    try:
        tk.get_action('thredds_get_metadata_info')(context, {'id': resource_id})
    except:
        return False

    return True

def get_current_datetime():
    import datetime
    return datetime.datetime.utcnow()
