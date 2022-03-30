Code style
=========================

In case you contribute code, we generally ask for following the code style we are using already.
This is a general Python style, with 4 spaces as the delimiter, nothing groundbreaking here :)

Formatting/Linting
------------------

Import sorting is controlled by `isort <https://pycqa.github.io/isort/>`__. An isort
configuration is part of the ``setup.cfg`` in the root directory.

For code formatting we use `Black <https://black.readthedocs.io/en/stable/index.html/>`__.

For linting we use `Flake8 <http://flake8.pycqa.org/en/latest/>`__.  A Flake8 configuration is
part of the ``setup.cfg`` in the root directory.

There is a helper script to reformat the code under ``support/run_formatter.py`` and the tests
will also verify this formatting.

Logging
--------

Python supports a number of different logging patterns - for more information see `Pyformat <https://pyformat.info/>`_
and `Formatting python log messages <https://reinout.vanrees.org/weblog/2015/06/05/logging-formatting.html>`_.
We request that the new format style is followed e.g.

.. code-block:: python3

   logger.info("Fetching common steps from '{}'.".format(url))
