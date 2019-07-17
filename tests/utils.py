def merge_two_dicts(x, y):
    """
    Python 2/3 compatible method to merge two dictionaries.

    Ref: https://stackoverflow.com/questions/38987/how-to-merge-two-dictionaries-in-a-single-expression

    :param x: Dictionary 1.
    :param y: Dictionary 2.
    :return: Merged dicts.
    """
    z = x.copy()   # start with x's keys and values
    z.update(y)    # modifies z with y's keys and values & returns None
    return z
