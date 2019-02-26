

Contributing to the project
===========================

We strongly advise to use `Virtualenv <https://virtualenv.pypa.io/en/stable/>`_ to develop Cekit. Please consult your package manager for the correct package name. Currently within Fedora 29 almost all the required packages are available as RPMs. A sample set of Ansible scripts that provide **all** pre-requistites for development are available `here <https://github.com/cekit/cekit/tree/develop/ansible>`_.

- If you are running inside the Red Hat infrastructure then ``rhpkg`` must be installed as well.
- Currently ``port_for==0.3.1`` must still be installed manually.

To create custom Python virtual environment please run following commands on your system:

.. code-block:: bash

    # Prepare virtual environment
    virtualenv ~/cekit
    source ~/cekit/bin/activate

    # Install as development version
    pip install -e <cekit directory>

    # Now you are able to run Cekit
    cekit --help

It is possible to ask virtualenv to inherit pre-installed system packages thereby reducing the virtualenv to a delta between what is installed and what is required. This is achived by using the flag ``--system-site-packages`` (See `here <https://virtualenv.pypa.io/en/latest/userguide/#the-system-site-packages-option>`_ for further information).

.. note::

   Every time you want to use Cekit you must activate Cekit Python virtual environment by executing ``source ~/cekit/bin/activate``

   For those using ZSH a useful addition is `Zsh-Autoswitch-VirtualEnv <https://github.com/MichaelAquilina/zsh-autoswitch-virtualenv>`_ the use of which avoids the labour of manually creating the virtualenv and activating it each time ; simply run ``mkvenv --system-site-packages`` initially and then it is handled automatically then on.



Running the tests
-----------------

To run the tests it is recommended to use ``tox``. To run a single function from a single test on a single version of python the following command may be used:

.. code-block:: bash

    tox -e py37 -- tests/test_validate.py::test_simple_image_build


Or, using pytest directly:

.. code-block:: bash

    pytest-3 tests/test_validate.py::test_image_test_with_multiple_overrides


Contributing to documentation
-----------------------------

We use the `reStructuredText <http://docutils.sourceforge.net/rst.html>`_ format to
write our documentation because this is the de-facto standard for Python documentation.
We use `Sphinx <http://www.sphinx-doc.org/en/stable/index.html>`_ tool to generate documentation
from reStructuredText files.

Published documentation lives on Read the Docs: `<https://cekit.readthedocs.io/>`_

reStructuredText
~~~~~~~~~~~~~~~~

A good guide to this format is available in the `Sphinx documentation <http://www.sphinx-doc.org/en/stable/rest.html>`_.

Local development
~~~~~~~~~~~~~~~~~

.. note::

    The documentation has its own ``requirements.txt``. As above we would recommend using
    `Virtualenv <https://virtualenv.pypa.io/en/stable/>`_ to use a clean development environment.
    The Ansible scripts above will install all documentation pre-requisites as well.

Support for auto generating documentation is avialable for local development. Run the command below.

.. code:: bash

    make preview

Afterwards you can see generated documentation at `<http://127.0.0.1:8000>`_. When you edit any file,
documentation will be regenerated and immediately available in your browser.

Guidelines
~~~~~~~~~~

Below you can find a list of conventions used to write CEKit documentation. Reference information on reStructuredText
may be found `here <http://docutils.sourceforge.net/rst.html>`_.

Headers
^^^^^^^

Because reStructredText does not enforce what characters are used to mark header
to be a certain level, we use following guidelines:

.. code::

    h1 header
    =========

    h2 header
    ---------

    h3 header
    ^^^^^^^^^

    h4 header
    *********
