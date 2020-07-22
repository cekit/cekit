Base images
===============================

.. contents::
    :backlinks: none

This chapter discusses support for creating images that extend the ``scratch`` image
to build base images.

Introduction
---------------------------------

.. tip::
    Please read the
    `Docker documentation on scratch base image <https://docs.docker.com/develop/develop-images/baseimages/#create-a-simple-parent-image-using-scratch>`__.

The ``scratch`` image is a special type of image. It is an empty image and the ``FROM scratch``
instruction in Dockerfile results in no-op when building the container image. There are a few
use-cases for such an image:

Storing native binaries
    It is very popular in the cloud-native era to use languages that produce native binaries
    which are packaged in a container image format and distributed this way. One of the most
    popular languages is `Golang <https://golang.org/>`_.

    .. tip::
        You may be interested in :doc:`multi-stage builds </handbook/multi-stage>` as well.
Storing shared content (for example metadata)
    Sometimes there is a requirement to store metadata (for example YAML files)
    in a container image so that it can be versioned and used elsewhere.

CEKit implementation
-----------------------

Support for ``scratch`` base image is a special case in CEKit. This means that some of the features
you are used to may not work properly.

You need to ensure that modules you are including are written in a way so these can be installed
and executed in an environment **without operating system libraries**.

In case of such container images it is important to understand how artifacts are
put inside of them. By default CEKit copies artifacts into a temporary directory which
are later handled by modules (copied to correct places, permissions are managed, etc).
For ``scratch`` container images it won't work, because we don't have the operating
system that would make it possible.

In this case, the ``dest`` keyword should be used to define the destination directory
of the particular artifact.

.. code-block:: yaml
    :caption: image.yaml
    :emphasize-lines: 3,19,22,28

    name: "cekit-scratch"
    version: "1.0.0"
    from: "scratch"
    description: "Minimal scratch example"

    labels:
        - name: "io.cekit.test"
          value: "This is a CEKit test label"

    envs:
        - name: "CEKIT_TEST"
          value: "test"

    artifacts:
        # Both files will be added to a /files directory in the container image
        # The /files directory itself will be created
        - name: "file1"
          path: metadata/test-file.txt
          dest: /files/
        - name: "file2"
          path: metadata/other.txt
          dest: /files/

        # Whole 'metadata' directory (path relative to image descriptor) will be copied to
        # the container and placed in /target directory
        - name: "dir"
          path: metadata
          dest: /target

In case of ``scratch`` container images it is safe to assume that following features are supported:

* Artifacts with ``dest`` property defined
* Environment variables
* Labels
* Entrypoint and command

Below you can find a multi-stage build which builds a Go binary in first stage and then it is
copied to the resulting image which is an empty container image. Additionally the binary is set as
an entrypoint.

.. code-block:: yaml
    :caption: image.yaml

    - name: builder
      version: 1.0.0
      from: golang:1.7.3

      modules:
        repositories:
          - path: modules

        install:
          # Module required to build the application
          - name: build

    - name: some/app
      version: 12
      from: scratch
      description: Our application

      artifacts:
        - name: application
          # Name of the image from where the binary will be copied
          image: builder
          # Path where the binary can be found in the 'builder' image
          path: /tmp/scripts/build/hello-world
          # Target file name of the artifact
          target: entrypoint
          # Destination directory in the image
          dest: /bin

      run:
        entrypoint: ["/bin/entrypoint"]

.. note::
    You can find above example in the `CEKit source repository <https://github.com/cekit/cekit/tree/develop/tests/images/multi-stage-scratch>`_. It's run as part of integration tests.
