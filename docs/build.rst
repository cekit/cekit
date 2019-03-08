Building images
================

CEKit supports following builder engines:

* Docker -- builds the container image using the Docker daemon, this is the default option
* OSBS -- builds the container image using `OSBS service <https://osbs.readthedocs.io>`_
* Buildah -- builds the container image using `Buildah <https://buildah.io/>`_
* Podman -- builds the container image using `Podman <https://podman.io/>`_

Executing builds
-----------------

You can execute container image build by running:

.. code:: bash

	  $ cekit build

**Global options

**Options affecting builder:**

* ``--dry-run`` -- Do not execute the build, just generate required files.
* ``--overrides`` -- Inline overrides in JSON format.
* ``--overrides-file`` -- Path to overrides file in YAML format.
* ``--add-help`` -- Include generated help files in the image.
* ``--help`` -- Show this message and exit.

**Sub-commands that are available are:**

* ``buildah`` --  Build using Buildah engine
* ``docker`` -- Build using Docker engine
* ``osbs`` -- Build using OSBS engine
* ``podman`` -- Build using Podman engine

**Buildah and Podman options are:**

* ``--pull`` -- ask a builder engine to check and fetch latest base image
* ``--tag`` -- an image tag used to build image (can be specified multiple times)
* ``--help`` -- Show this message and exit.

**Docker options are:**

* ``--pull`` -- ask a builder engine to check and fetch latest base image
* ``--tag`` -- an image tag used to build image (can be specified multiple times)
* ``--no-squash`` -- do not squash the image after build is done.
* ``--help`` -- Show this message and exit.

**OSBS options are:**

* ``--release`` -- perform a OSBS release build
* ``--tech-preview`` -- updates image descriptor ``name`` key to contain ``-tech-preview`` suffix in family part of the image name
* ``---user`` -- alternative user passed to `rhpkg --user`
* ``--nowait`` -- run `rhpkg container-build` with `--nowait` option specified
* ``--stage`` -- use ``rhpkg-stage`` tool instead of ``rhpkg``
* ``--koji-target`` -- overrides the default ``koji`` target
* ``--commit-msg`` -- custom commit message for dist-git
* ``--help`` -- Show this message and exit.


Docker build
^^^^^^^^^^^^^^^^

This is the default way to build an container image. The image is build utilizing Docker daemon via Python binding.

**Example:** Building a docker image

.. code:: bash

	  $ cekit build


OSBS build
^^^^^^^^^^^^^^^

This build engine is using ``rhpkg`` or ``fedpkg`` tool to build the image using OSBS service. By default
it performs scratch build. If you need a release build you need to specify ``--release`` parameter.

**Example:** Performing scratch build

.. code:: bash

	  $ cekit build osbs


**Example:** Performing release build

.. code:: bash

	  $ cekit build osbs --release


Buildah build
^^^^^^^^^^^^^

This build engine is based on `Buildah <https://buildah.io>`_. Buildah still doesn't
support non-privileged builds so you need to have **sudo** configured to run `buildah` as a root user on
your desktop.

.. note::
   If you need to use any non default registry, please update `/etc/containers/registry.conf` file.


**Example:** Building image using Buildah

.. code:: bash

	  $ cekit build buildah



Podman build
^^^^^^^^^^^^^

This build engine is based on `Podman <https://podman.io>`_. Podman will perform non-privileged builds so
no special configuration is required.
