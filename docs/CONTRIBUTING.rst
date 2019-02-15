

Contributing to the project
===========================

We strongly advise to use `Virtualenv <https://virtualenv.pypa.io/en/stable/>`_ to install Cekit. Please consult your package manager for the correct package name.

To create custom Python virtual environment please run following commands on your system:

.. code-block:: bash

    # Prepare virtual environment
    virtualenv ~/cekit
    source ~/cekit/bin/activate

    # Install Cekit
    # Execute the same command to upgrade to latest version
    pip install -U cekit

    # Now you are able to run Cekit
    cekit --help

It is possible to ask virtualenv to inherit pre-installed system packages thereby reducing the virtualenv to a delta between what is installed and what is required. This is achived by using the flag ``--system-site-packages`` (See `here <https://virtualenv.pypa.io/en/latest/userguide/#the-system-site-packages-option>`_ for further information).

.. note::

   Every time you want to use Cekit you must activate Cekit Python virtual environment by executing ``source ~/cekit/bin/activate``

.. note::
   For those using ZSH a useful addition is `Zsh-Autoswitch-VirtualEnv <https://github.com/MichaelAquilina/zsh-autoswitch-virtualenv>`_ the use of which avoids the labour of manually creating the virtualenv and activating it each time.

Currently within Fedora 29 almost all the required packages are available as RPMs; non-python packages are:

- buildah
- docker
- fedpkg | rhpkg
- git
- make
- odcs-client
- podman

Python RPMs are:

- python3-behave
- python3-colorlog
- python3-docker
- python3-docker-squash
- python3-jinja2
- python3-lxml
- python3-mock
- python3-pykwalify
- python3-pytest
- python3-pytest-mock
- python3-pyyaml
- python3-tox
- python3-virtualenv

For documentation, the following RPMs apply ( ``port_for==0.3.1`` must still be installed manually )

- python3-argh
- python3-livereload
- python3-pathtools
- python3-sphinx
- python3-sphinx-autobuild
- python3-watchdog


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

    Consider using `Virtualenv <https://virtualenv.pypa.io/en/stable/>`_ to use a clean development environment.
    If you are not using Virtualenv we suggest to run below ``pip`` command with the ``--user`` flag at least.

You need to install required tools to be able to generate documentation locally.

.. code:: bash

    pip install -U -r requirements.txt

Support for auto generating documentation is avialable for local development. Run the command below.

.. code:: bash

    make preview

Afterwards you can see generated documentation at `<http://127.0.0.1:8000>`_. When you edit any file,
documentation will be regenerated and immediately available in your browser.

Guidelines
~~~~~~~~~~

Below you can find a list of conventions used to write CEKit documentation.

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
