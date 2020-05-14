from deepdiff.deephash import DeepHash
from deepdiff.helper import DELTA_VIEW, numbers, strings
from collections.abc import Mapping, Iterable


class DistanceMixin:

    def get_deep_distance(self):
        """
        Gives a numeric value for the distance of t1 and t2 based on how many operations are needed to convert
        one to the other.

        This is a similar concept to the Levenshtein Edit Distance but for the structured data and is it is designed
        to be between 0 and 1.

        A distance of zero means the objects are equal and a distance of 1 is very far.

        Note: The deep distance calculations are currently only internally used when ignore_order=True so
        it is implemented as a part of an algorithm that ONLY runs when ignore_order=True.
        It DOES NOT work properly when ignore_order=False (default).
        If you have a use case for the deep distance to be calculated when ignore_order=False, then please open a ticket.

        Info: The current algorithm is based on the number of operations that are needed to convert t1 to t2 divided
        by the number of items that make up t1 and t2.
        """
        if not self.hashes:
            raise ValueError(
                'Only during the hash calculations, the objects hierarchical '
                'counts are evaluated. As a result, the deep distance is only calculated when ignore_order=True.'
                'If you have a usage for this function when ignore_order=False, then let us know')
        if not self.ignore_order:
            raise ValueError(
                'The deep distance is only calculated when ignore_order=True in the current implementation.'
            )
        item = self if self.view == DELTA_VIEW else self._to_delta_dict(report_repetition_required=False)
        diff_length = _get_diff_length(item)

        if diff_length == 0:
            return 0

        t1_len = self.__get_item_rough_length(self.t1)
        t2_len = self.__get_item_rough_length(self.t2)

        return diff_length / (t1_len + t2_len)

    def __get_item_rough_length(self, item, parent='root'):
        """
        Get the rough length of an item.
        It is used as a part of calculating the rough distance between objects.

        **parameters**

        item: The item to calculate the rough length for
        parent: It is only used for DeepHash reporting purposes. Not really useful here.
        """
        length = DeepHash.get_key(self.hashes, key=item, default=None, extract_index=1)
        if length is None:
            DeepHash(
                item,
                hashes=self.hashes,
                parent='root',
                apply_hash=True,
                **self.deephash_parameters,
            )
            length = DeepHash.get_key(self.hashes, key=item, default=None, extract_index=1)
        return length


def _get_diff_length(item):
    """
    Get the number of operations in a diff object.
    It is designed mainly for the delta view output
    but can be used with other dictionary types of view outputs too.
    """

    length = 0
    if hasattr(item, '_diff_length'):
        length = item._diff_length
    elif isinstance(item, Mapping):
        for key, subitem in item.items():
            if key in {'iterable_items_added_at_indexes', 'iterable_items_removed_at_indexes'}:
                # import pytest; pytest.set_trace()
                new_subitem = {}
                for path_, indexes_to_items in subitem.items():
                    used_value_ids = set()
                    new_indexes_to_items = {}
                    for k, v in indexes_to_items.items():
                        v_id = id(v)
                        if v_id not in used_value_ids:
                            used_value_ids.add(v_id)
                            new_indexes_to_items[k] = v
                    new_subitem[path_] = new_indexes_to_items
                subitem = new_subitem
            length += _get_diff_length(subitem)
    elif isinstance(item, numbers):
        length = 1
    elif isinstance(item, strings):
        length = 1
    elif isinstance(item, Iterable):
        for subitem in item:
            length += _get_diff_length(subitem)
    elif isinstance(item, type):  # it is a class
        length = 1
    else:
        if hasattr(item, '__dict__'):
            for subitem in item.__dict__:
                length += _get_diff_length(subitem)

    try:
        item._diff_length = length
    except Exception:
        pass
    return length