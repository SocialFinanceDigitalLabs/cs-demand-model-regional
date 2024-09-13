from ssda903.config import Costs


def get_cost_items_for_category(category_label: str):
    """
    Takes a placement category label and returns related enum costs in a list
    """
    cost_items = []
    for cost in Costs:
        if cost.value.category.label == category_label:
            cost_items.append(cost.value)
    return cost_items
