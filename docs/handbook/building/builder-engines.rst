Supported builder engines
================================

.. contents::
    :backlinks: none

CEKit supports following builder engines:

* :ref:`Docker builder <handbook/building/builder-engines:Docker builder>` -- builds the container image using `Docker <https://docs.docker.com/>`__
* :ref:`OSBS builder <handbook/building/builder-engines:OSBS builder>` -- builds the container image using `OSBS service <https://osbs.readthedocs.io>`__
* :ref:`Buildah builder <handbook/building/builder-engines:Buildah builder>` -- builds the container image using `Buildah <https://buildah.io/>`__
* :ref:`Podman builder <handbook/building/builder-engines:Podman builder>` -- builds the container image using `Podman <https://podman.io/>`__

Docker builder
---------------------------

This builder uses Docker daemon as the build engine. Interaction with Docker daemon is done via Python binding.

Input format
    Dockerfile
Parameters
    * ``--pull`` -- ask a builder engine to check and fetch latest base image
    * ``--tag`` -- an image tag used to build image (can be specified multiple times)
    * ``--no-squash`` -- do not squash the image after build is done.

Example
    Building Docker image

    .. code-block:: bash

        $ cekit build docker

Docker environment variables
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

It is possible to use environment variables to let CEKit know where is the Docker daemon
located it should connect to.

.. note::
    Read more about `Docker daemon settings related to exposing it to clients <https://docs.docker.com/engine/reference/commandline/dockerd/#daemon-socket-option>`__.

By default, if you do not specify anything, **CEKit will try to use a locally running Docker daemon**.

If you need to customize this behavior (for example when you want to use Docker daemon
running in a VM) you can set following environment variables:

``DOCKER_HOST``
    The ``DOCKER_HOST`` environment variable is where you specify where the Daemon is running. It supports
    multiple protocols, but the most widely used ones are: ``unix://`` (where you specify path to a local
    socket) and ``tcp://`` (where you can define host location and port).

    Examples of ``DOCKER_HOST``: ``unix:///var/run/docker.sock``, ``tcp://192.168.22.33:1234``.

    Depending how your daemon is configured you may need to configure settings related to encryption.

    .. code-block:: bash

        # Connect to a remote Docker daemon
        $ DOCKER_HOST="tcp://192.168.22.33:1234" cekit build docker
``DOCKER_TLS_VERIFY``
    You can set ``DOCKER_TLS_VERIFY`` to a non-empty value to indicate that the TLS verification should
    take place. By default certificate verification is **disabled**.
``DOCKER_CERT_PATH``
    You can point ``DOCKER_CERT_PATH`` environment variable to a directory containing certificates to use when
    connecting to the Docker daemon.


OSBS builder
---------------------------

This build engine is using ``rhpkg`` or ``fedpkg`` tool to build the image using OSBS service. By default
it performs **scratch build**. If you need a proper build you need to specify ``--release`` parameter.

Input format
    Dockerfile
Parameters
    * ``--release`` -- perform an OSBS release build
    * ``--tech-preview`` -- build tech preview image, see :ref:`below for more information <handbook/building/builder-engines:Tech preview images>`
    * ``--user`` -- alternative user passed to build task
    * ``--nowait`` -- do not wait for the task to finish
    * ``--stage`` -- use stage environment
    * ``--koji-target`` -- overrides the default ``koji`` target
    * ``--commit-message`` -- custom commit message for dist-git

Example
    Performing scratch build

    .. code-block:: bash

        $ cekit build osbs

    Performing release build

    .. code-block:: bash

        $ cekit build osbs --release

Tech preview images
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. deprecated:: 3.3
    Use the :ref:`overrides feature <handbook/overrides:Overrides>` instead:

    .. code-block:: bash

        $ cekit build --overrides '{"name": "custom-family-tech-preview/project-8-centos7"}' osbs

The OSBS builder has support for building a tech preview image without modifying the image source.
The only difference between a regular image and the tech preview image is the resulting
name of the image. Tech preview images contain the ``-tech-preview`` suffix in the image family
of the name.

.. code-block:: bash

    $ cekit build osbs --tech-preview

.. note::
    You can combine the ``--tech-preview`` preview switch with ``--release`` switch.

Example
    The ``custom-family/project-8-centos7`` image built with the ``--tech-preview`` switch will become
    ``custom-family-tech-preview/project-8-centos7``.

Buildah builder
---------------------------

This build engine is using `Buildah <https://buildah.io>`_.

.. note::
   If you need to use any non default registry, please update ``/etc/containers/registry.conf`` file.

Input format
    Dockerfile
Parameters
    * ``--pull`` -- ask a builder engine to check and fetch latest base image
    * ``--tag`` -- an image tag used to build image (can be specified multiple times)

Example
    Build image using Buildah

    .. code-block:: bash

        $ cekit build buildah

    Build image using Buildah and tag it as ``example/image:1.0``

    .. code-block:: bash

        $ cekit build buildah --tag example/image:1.0

Podman builder
---------------------------

This build engine is using `Podman <https://podman.io>`_. Podman will perform non-privileged builds so
no special configuration is required.

Input format
    Dockerfile
Parameters
    * ``--pull`` -- ask a builder engine to check and fetch latest base image
    * ``--tag`` -- an image tag used to build image (can be specified multiple times)

Example
    Build image using Podman

    .. code-block:: bash

        $ cekit build podman

    Build image using Podman

    .. code-block:: bash

        $ cekit build podman --pull
