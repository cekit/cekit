Code style
=========================

In case you contribute code, we generally ask for following the code style we are using already.
This is a general Python style, with 4 spaces as the delimiter, nothing groundbreaking here :)

Formatting
-----------

For code formatting we use `Flake8 <http://flake8.pycqa.org/en/latest/>`__. You can find a ``.flake8``
configuration file in the root directory.

Linting
-----------

Additionally we check for code errors with `Pylint <https://www.pylint.org/>`__. We provide a
``.pylintrc`` file in the root directory which defines differences from the default
Pylint configuration. Your IDE may help with linting your code too!

Logging
--------

Python supports a number of different logging patterns - for more information see `Pyformat <https://pyformat.info/>`_
and `Formatting python log messages <https://reinout.vanrees.org/weblog/2015/06/05/logging-formatting.html>`_.
We request that the new format style is followed e.g.

.. code-block:: python3

   logger.info("Fetching common steps from '{}'.".format(url))
