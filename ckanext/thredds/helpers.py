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
        return parent
    except:
        return None


def get_children_datasets(package_id):
    ctx = {'model': model}

    try:
        relationships = tk.get_action('package_relationships_list')(ctx, {'id': package_id, 'rel': 'parent_of'})

        children = []

        for r in relationships:
            child = tk.get_action('package_show')(ctx, {'id': r['object']})
            children.append(child)

        return children
    except:
        return None
