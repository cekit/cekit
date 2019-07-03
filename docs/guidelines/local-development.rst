Local development
==========================

Developing image locally is an important part of the workflow. It needs to provide
a simple way to reference parts of the image we changed. Executing a local build with our
changes should be easily done too.


Referencing customized modules
--------------------------------

CEKit enables you to use a work in progress modules to build the image by using
its overrides system. As an example, imagine we have very simple image which is using
one module from a remote Git repository, like this:

.. code-block:: yaml

    schema_version: 1

    name: cekit/example-jdk8
    version: 1.0
    from: centos:7
    description: "JDK 8 image"

    modules:
      repositories:
        # Add a shared module repository located on GitHub. This repository
        # can contain several modules.
        - git:
            url: https://github.com/cekit/example-common-module.git
            ref: master

    # Install selected modules (in order)
    install:
      - name: jdk8
      - name: user

Now imagine, we have found a bug in its ``jdk8`` module. We will clone the module
repository locally by executing:

.. code-block:: bash

  $ git clone https://github.com/cekit/example-common-module.git ~/repos/example-common-module

Then we will create ``override.yaml`` file next to the ``image.yaml``. Override.yaml should look like this:

.. code-block:: yaml

  modules:
    repositories:
      - path: "/home/user/repo/cct_module"

Now we can build the image using overridden module by executing:

.. code-block:: bash

  $ cekit generate --overrides-file overrides.yaml

When your work is finished, commit and push your changes to a module repository.

Injecting local artifacts
----------------------------

During module/image development there can be a need to use locally built artifact instead of a released one.
The easiest way to inject such artifact is to use override mechanism.

Imagine that you have an artifact defined in following way:

.. code-block:: yaml

    artifacts:
        - name: jolokia
          md5: d31c6b1525e6d2d24062ef26a9f639a8
          url: https://maven.repository.redhat.com/ga/org/jolokia/jolokia-jvm/1.5.0.redhat-1/jolokia-jvm-1.5.0.redhat-1-agent.jar

You want to inject a local build of new version of our artifact. To archive it you need to create following override:

.. code-block:: yaml

    artifacts:
        - name: jolokia
          path: /tmp/build/jolokia.jar

Please note that the ``name`` key is used to identify which artifact we are going to override.

Whenever you override artifact, all previous checksums are removed too. If you want your new artifact to
pass integrity checks you need to define checksum also in overrides in a following way:

.. code-block:: yaml

    artifacts:
        - name: jolokia
          md5: d31c6b1525e6d2d24062ef26a9f639a8
          path: /tmp/build/joloika.jar

Using Docker cache
--------------------

.. versionadded:: 3.3.0

Docker has support for caching layers. This is very convenient when you are developing images. It saves time by
not rebuilding the whole image on any change, but instead it rebuilds layers that were changed only.

You can read more about it `in Docker's documentation <https://docs.docker.com/develop/develop-images/dockerfile_best-practices/#leverage-build-cache>`__.

In version ``3.3.0`` CEKit we optimized the way we generate Dockerfile making it much easier to fully
leverage the caching mechanism.

In order to make most of this feature we strongly suggest to execute Docker build with the the ``--no-squash``
parameter. This will make sure that the intermediate layers won't be removed. In other case, the
squashing post-processing will take place and any intermediate layers will be cleaned afterwards
effectively losing cached layers.

.. code-block:: bash

    $ cekit build docker --no-squash

.. warning::

    You need to be aware that rebuilding a Docker image numerous times with the ``--no-squash``
    option will leave many dangling layers that could fill your Docker storage. To prevent
    this you need to remove unused images from time to time. The ``docker system prune -a`` command
    may be useful.

.. note::
    Please note that ``--no-squash`` switch may be only useful when developing the image.
    We strongly suggest to not use it to build the final image.
