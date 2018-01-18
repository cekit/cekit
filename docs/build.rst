Building image
================

Concreate supports following builder engines:

* ``Docker`` -- build the container image using `docker build <https://docs.docker.com/engine/reference/commandline/build/>`_ command and it default option
* ``OSBS`` -- build the container image using `OSBS service <https://osbs.readthedocs.io>`_

Executing builds
-----------------

You can execute an container image build by running:

.. code:: bash

	  $ concreate build

**Options affecting builder:**

* ``--tag`` -- an image tag used to build image (can be specified multiple times)
* ``--build-engine`` -- a builder engine to use ``osbs`` or ``docker`` [#f1]_
* ``--build-osbs-release`` [#f2]_ -- perform a OSBS release build
* ``--build-osbs-user`` -- alternative user passed to `rhpkg --user`
* ``--build-osbs-nowait`` -- run `rhpkg container-build` with `--nowait` option specified
* ``--build-tech-preview`` [#f2]_ -- updates image descriptor ``name`` key to contain ``-tech-preview`` suffix in family part of the image name
  
  **Example**: If your ``name`` in image descriptor is: ``jboss-eap-7/eap7``, generated name will be: ``jboss-eap-7-tech-preview/eap7``.

.. [#f1] docker build engine is default
.. [#f2] option is valid on for ``osbs`` build engine

Docker build
^^^^^^^^^^^^^^^^

This is the default way to build an container image. The image is build using ``docker build``.

**Example:** Building a docker image

.. code:: bash

	  $ concreate build


OSBS build
^^^^^^^^^^^^^^^

This build is using ``rhpkg container-build`` to build the image using OSBS service. By default
it performs scratch build. If you need a release build you need to specify ``--build-osbs-release`` parameter.

**Example:** Performing scratch build

.. code:: bash

	  $ concreate build --build-engine=osbs


**Example:** Performing release build

.. code:: bash

	  $ concreate build --build-engine=osbs --build-osbs-release
