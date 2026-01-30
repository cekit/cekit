Multi-stage builds
====================


This chapter discusses support for multi-stage builds in CEKit.

Introduction
---------------------------------

.. tip::
    Please read the
    `Docker documentation on multi-stage builds <https://docs.docker.com/develop/develop-images/multistage-build/>`__.

Multi-stage builds define a process to build final image that uses intermediate images in the workflow.
Such workflow is useful when we want to build some artifacts (applications, binaries, etc) as
part of the build, but we are not interested in all dependencies that are required to build them.

Multi-stage builds can help with it, because intermediate images used as part of the build
are thrown away after the build is finished. The effective image can contain binaries built in
previous stages without the need to install all the build time dependencies there. This makes
it possible to decrease the size of the image significantly. Other positive aspect is that
having less packages installed in the image means that we are less exposed to CVE's making
the image more secure.


CEKit implementation
-----------------------

In CEKit we use :doc:`image descriptor </descriptor/index>` to define the image. Descriptor format was extended
and allows now a list of image descriptors.

.. code-block:: yaml
    :caption: image.yaml
    :emphasize-lines: 1,16

    - name: builder
      version: 1.0.0
      from: centos:7
      description: Some base image

      modules:
        repositories:
          - path: modules

        install:
          # Module providing environment required to build the application
          - name: python
          # Module required to build the application
          - name: build

    - name: some/app
      version: 12
      from: centos:7
      description: Our application

      modules:
        repositories:
          - path: modules

        # Install selected modules (in order)
        install:
          - name: setuptools
          # This module is responsible for fetching application built in previous stage
          - name: app

If a list of more than one image is found -- multi-stage builds are assumed.

For multi-stage builds you have have multiple intermediate images and always just one final image.
In CEKit this means that the **last image defined in the descriptor is the final one**, every other
image is an intermediate image.

Let's go back to our example above.

We have two images defined: ``builder`` and ``some/app``. As the name suggest,
the first one is the builder (intermediate) image which will contain the build-time dependencies
and where the actual artifact will be built.

.. note::
    Although it is possible to use all keys available to use in an
    :doc:`image descriptor </descriptor/image>` when defining builder images,
    some of them does not have any effect. A few examples of such keys can be found below:

    * ``ports``
    * ``volumes``
    * ``run``
    * ``help``

The second image is the final image where we will place the built artifact. But how to do it? Let's take
a look at the ``app`` module which defines a special artifact.

.. code-block:: yaml
    :caption: module.yaml
    :emphasize-lines: 8-14

    name: app
    version: 1.0

    packages:
       install:
          - python-requests

    artifacts:
        - name: application
          image: builder
          path: /path/to/application/inside/the/builder/image.jar

        - image: builder
          path: /path/to/lib.jar

    execute:
        - script: install.sh

This artifact is called :ref:`image content resource <descriptor/image:Image source artifacts>` and it does
define artifact that is located in an image built in
previous stage of the multi-stage build workflow. You do not need to define anything in the builder image.
It's responsibility is only to build the artifacts which can be referenced in the final image.

In our case we define two artifacts, both from the ``builder`` image.

The first one will become available as ``/tmp/artifacts/application`` and the second one
as ``/tmp/artifacts/lib.jar`` in the final image.

.. tip::
    You can change the destination as well as the target file name of artifacts. See
    how it can be done using :ref:`appropriate keys in the artifact <descriptor/image:Common artifact keys>`.

Image source artifacts can be handled and installed to the correct place,
as you would normally do with other types of artifacts.
