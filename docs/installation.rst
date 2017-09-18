Installation
============

We strongly advise to use `Virtualenv <https://virtualenv.pypa.io/en/stable/>`_ to install Concreate.

If you are on Fedora/RHEL please install the ``python-virtualenv`` package. If you use different operating system please consult your package namager of choice for the correct package name.

.. code-block:: bash

    # Prepare virtual environment
    virtualenv ~/concreate
    source ~/concreate/bin/activate

    # Install Concreate
    # Execute the same command to upgrade to latest version
    pip install -U concreate

    # Now you are able to run Concreate
    concreate --help

Requirements
------------

To build container images you need to have Docker installed on your system.
