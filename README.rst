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

History
-------

Concreate originates from the `Dogen <https://github.com/jboss-dockerfiles/dogen>`_ tool. Dogen was developed for over two years and served us well, but we decided to make it a first class citizen and promote using abstract image descriptors. At the same time we wanted to add new set of features which made the "Dockerfile generator" tagline inaccurate and we decided to start fresh under a new project. In any case, this is the Dogen project evolution.

Status
------

This project is currently in development. Initial release should be avaialble shortly. Support for multiple target platforms is planned in future, but currently only Docker is supported.

Requirements
------------

To build container images

- Docker
