from collections import OrderedDict


def merge_dicts(*dict_args):
    """
    Python 2/3 compatible method to merge dictionaries.

    Ref: https://stackoverflow.com/questions/38987/how-to-merge-two-dictionaries-in-a-single-expression

    :param dict_args: Dictionaries.
    :return: Merged dicts.
    """
    result = OrderedDict()
    for dictionary in dict_args:
        result.update(dictionary)
    return result
