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

Python supports a number of different logging patterns - for more information see `here <https://docs.python
.org/3/tutorial/inputoutput.html>`_ and `Python's F-String for String Interpolation and Formatting
<https://realpython.com/python-f-strings/>`_ and `here <https://martinheinz.dev/blog/70>`_

Given most `performance measurements <https://www.reddit
.com/r/Python/comments/pivojb/performance_comparison_of_string_formatting/>`_ show f-strings to be preferred we request
that their style is followed e.g.

.. code-block:: python3

   logger.info(f"Fetching common steps from '{url}'.")
