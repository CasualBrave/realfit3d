"""CPU-only request contracts shared by Web and CLI."""
import math


def body_parameters(height, weight, gender):
    height, weight = float(height), float(weight)
    if (not math.isfinite(height) or not math.isfinite(weight) or not 1 <= height <= 2.2
            or not 25 <= weight <= 180 or gender not in ('female', 'male')):
        raise ValueError('Invalid body measurements or gender')
    return dict(height=height, weight=weight, gender=gender)


def select_outfit(catalog, upper_id, lower_id, motion):
    garments = {g['name']: g for g in catalog['garments']}
    upper, lower = garments.get(upper_id), garments.get(lower_id)
    if not upper or upper['slot'] != 'upper' or not lower or lower['slot'] != 'lower':
        raise ValueError('Select one upper and one lower garment')
    index = int(motion)
    if not 0 <= index < len(catalog['motions']):
        raise ValueError('Invalid motion')
    return upper, lower, catalog['motions'][index]['path']


def outfit_name(upper, lower, gender):
    name = lower['name'] + '+' + upper['name']
    return name if gender == 'female' else name + '_' + gender
