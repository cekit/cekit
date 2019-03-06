Building images
================

CEKit supports following builder engines:

* Docker -- builds the container image using the Docker daemon, this is the default option
* OSBS -- builds the container image using `OSBS service <https://osbs.readthedocs.io>`_
* Buildah -- builds the container image using `Buildah <https://github.com/projectatomic/buildah>`_

Executing builds
-----------------

You can execute container image build by running:

.. code:: bash

	  $ cekit build

**Options affecting builder:**

* ``--tag`` -- an image tag used to build image (can be specified multiple times)
* ``--redhat`` -- build image using Red Hat defaults. See :ref:`Configuration section for Red Hat specific options<redhat_env>` for additional details.
* ``--add-help`` -- add generated ``help.md`` file to the image
* ``--no-add-help`` -- don't add generated ``help.md`` file to the image
* ``--work-dir`` -- sets CEKit works directory where dist_git repositories are cloned into See :ref:`Configuration section for work_dir<workdir_config>`
* ``--package-manager`` -- allows selecting between different package managers such as ``yum`` or ``microdnf``. Defaults to ``yum```
* ``--build-engine`` -- a builder engine to use ``osbs``, ``buildah`` or ``docker``, deafult is ``docker``
* ``--build-pull`` -- ask a builder engine to check and fetch latest base image
* ``--build-osbs-stage`` -- use ``rhpkg-stage`` tool instead of ``rhpkg``
* ``--build-osbs-release`` -- perform a OSBS release build
* ``--build-osbs-user`` -- alternative user passed to `rhpkg --user`
* ``--build-osbs-target`` -- overrides the default ``rhpkg`` target
* ``--build-osbs-commit-msg`` -- custom commit message for dist-git
* ``--build-osbs-nowait`` -- run `rhpkg container-build` with `--nowait` option specified
* ``--build-tech-preview`` -- updates image descriptor ``name`` key to contain ``-tech-preview`` suffix in family part of the image name

Docker build
^^^^^^^^^^^^^^^^

This is the default way to build an container image. The image is build utilizing Docker daemon via Python binding.

**Example:** Building a docker image

.. code:: bash

	  $ cekit build


OSBS build
^^^^^^^^^^^^^^^

This build engine is using ``rhpkg`` or ``fedpkg`` tool to build the image using OSBS service. By default
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
