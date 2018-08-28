Building image
================

Cekit supports following builder engines:

* ``Docker`` -- build the container image using `docker build <https://docs.docker.com/engine/reference/commandline/build/>`_ command and it default option
* ``OSBS`` -- build the container image using `OSBS service <https://osbs.readthedocs.io>`_
* ``Buildah`` -- build the container image using `Buildah <https://github.com/projectatomic/buildah>`_

Executing builds
-----------------

You can execute an container image build by running:

.. code:: bash

	  $ cekit build

**Options affecting builder:**

* ``--tag`` -- an image tag used to build image (can be specified multiple times)
* ``--redhat`` -- build image using Red Hat defaults. See :ref:`Configuration section for Red Hat specific options<redhat_env>` for additional details.
* `--add-help`` -- add generated `help.md` file to the image
* `--no-add-help`` -- don't add generated `help.md` file to the image
* ``--work-dir`` -- sets Cekit works directory where dist_git repositories are cloned into See :ref:`Configuration section for work_dir<workdir_config>`
* ``--build-engine`` -- a builder engine to use ``osbs``, ``buildah`` or ``docker`` [#f1]_
* ``--build-pull`` -- ask a builder engine to check and fetch latest base image
* ``--build-osbs-stage`` -- use ``rhpkg-stage`` tool instead of ``rhpkg``
* ``--build-osbs-release`` [#f2]_ -- perform a OSBS release build
* ``--build-osbs-user`` -- alternative user passed to `rhpkg --user`
* ``--build-osbs-target`` -- overrides the default ``rhpkg`` target
* ``--build-osbs-commit-msg`` -- custom commit message for dist-git
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

	  $ cekit build


OSBS build
^^^^^^^^^^^^^^^

This build engine is using ``rhpkg container-build`` to build the image using OSBS service. By default
it performs scratch build. If you need a release build you need to specify ``--build-osbs-release`` parameter.

**Example:** Performing scratch build

.. code:: bash

	  $ cekit build --build-engine=osbs


**Example:** Performing release build

.. code:: bash

	  $ cekit build --build-engine=osbs --build-osbs-release


Buildah build
^^^^^^^^^^^^^

This build engine is based on `Buildah <https://github.com/projectatomic/buildah>`_. Buildah still doesn't
support non-privileged builds so you need to have **sudo** configured to run `buildah` as a root user on
your desktop.

.. note::
   If you need to use any non default registry, please update `/etc/containers/registry.conf` file.


**Example:** Building image using Buildah

.. code:: bash

	  $ cekit build --build-engine=buildah
