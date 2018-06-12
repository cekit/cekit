Cekit
=====

About
-----

Container image creation tool. Cekit was previously known as Concreate. If your migrating from concreate tool, please follow
upgrade instructions `<http://cekit.readthedocs.io/en/develop/installation.html#installing-cekit>`_.

Cekit helps to build container images from image definition files with strong focus on modularity and code reuse.

Features
--------

- `Building container images <http://cekit.readthedocs.io/en/develop/build.html>`_ from YAML image definitions
- `Integration/unit testing <http://cekit.readthedocs.io/en/develop/test.html>`_ of images
- Releasing container images by building it in Red Hat supported build system

Installation
------------

If you are running Fedora, you can install Cekit easily via:

.. code-block:: bash

    dnf copr enable @cekit/cekit
    dnf install python3-cekit

For other platforms, please refer to `documentation <http://cekit.readthedocs.io/en/develop/installation.html>`_.

Usage
-----
First steps tutorial is under construction, for now please refer to the ``cekit --help`` output.

Documentation
-------------

`Documentation is available here <http://cekit.readthedocs.io/en/develop/>`_.

