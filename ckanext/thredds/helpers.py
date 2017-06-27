import ckan.plugins.toolkit as tk
import ckan.lib.base as base

import ckan.model as model
import ckan.logic as logic


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
            child = tk.get_action('package_show')(ctx, {'id': r['object']})
            if child['private'] is False and child['state'] == 'active':
                children.append(child)
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
