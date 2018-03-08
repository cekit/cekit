Cekit
=====

About
-----

Container image creation tool. Cekit was previously known as Concreate. If your migrating from concreate tool, please follow
upgrade instructions <http://concreate.readthedocs.io/en/develop/upgrade.html>`_.

Cekit helps to build container images from image definition files with strong focus on modularity and code reuse.

Features
--------

- `Building container images <http://concreate.readthedocs.io/en/develop/build.html>`_ from YAML image definitions
- `Integration/unit testing <http://concreate.readthedocs.io/en/develop/test.html>`_ of images
- Releasing container images by building it in Red Hat supported build system

Installation
------------

If you are running Fedora, you can install Concreate easily via:

.. code-block:: bash

    dnf copr enable @cekit/cekit
    dnf install python3-cekit

For other platforms, please refer to `documentation <http://concreate.readthedocs.io/en/develop/installation.html>`_.

Usage
-----
First steps tutorial is under construction, for now please refer to the ``concreate --help`` output.

Documentation
-------------

`Documentation is available here <http://concreate.readthedocs.io/en/develop/>`_.

History
-------

Cekit originates from the `Dogen <https://github.com/jboss-dockerfiles/dogen>`_ tool. Dogen was developed for over two years and served us well, but we decided to make it a first class citizen and promote using abstract image descriptors. At the same time we wanted to add new set of features which made the "Dockerfile generator" tagline inaccurate and we decided to start fresh under a new project. In any case, this is the Dogen project evolution.


