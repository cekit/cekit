Running tests
===============

To run the tests it is recommended to use ``tox``. To run a single function from a single test on a single version of python the following command may be used:

.. code-block:: bash

    tox -e py37 -- tests/test_validate.py::test_simple_image_build


Or, using pytest directly:

.. code-block:: bash

    pytest-3 tests/test_validate.py::test_image_test_with_multiple_overrides