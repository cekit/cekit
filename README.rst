Concreate
=========

Container image creation tool.

About
-----

Concreate helps to build container images from image definition files.

Features
--------

- Building container images from YAML image definitions
- (not yet available) Running tests on built images
- (not yet available) Releasing container image by building it in Red Hat supported build system

Status
------

This project is currently in development. Initial release should be avaialble shortly. Support for multiple target platforms is planned in future, but currently only Docker is supported.

Installation
------------

We strongly advise to use `Virtualenv <https://virtualenv.pypa.io/en/stable/>`_ to install Concreate. If you are on Fedora/RHEL please install the ``python-virtualenv`` package. If you use different operating system please consult your package namager of choice for the correct package name.

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
^^^^^^^^^^^^

To build container images you need to have Docker installed on your system.

Usage
-----

Please refer to the ``concreate --help`` output.

Documentation
-------------

Documentation is available in the `docs <docs/>`_ directory.

History
-------

Concreate originates from the `Dogen <https://github.com/jboss-dockerfiles/dogen>`_ tool. Dogen was developed for over two years and served us well, but we decided to make it a first class citizen and promote using abstract image descriptors. At the same time we wanted to add new set of features which made the "Dockerfile generator" tagline inaccurate and we decided to start fresh under a new project. In any case, this is the Dogen project evolution.


