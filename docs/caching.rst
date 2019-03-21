Artifact caching
================

.. contents::
    :backlinks: none

In this chapter we will go through the caching feature of CEKit.

CEKit has a built-in cache for artifacts. It's purpose is to speed up the build process for subsequent builds.

Technical design
-----------------

By default cached artifacts are located in the ``~/.cekit/cache/`` directory.

.. note::
    Cache location can be changed when you specify the ``--work-dir`` parameter. In such case cache
    will be located in a ``cache`` directory located inside the directory specified by the ``--work-dir`` parameter.

Every cached artifact is identified with a UUID (version 4). This identifier is also used as the file name (in the
cache directory) for the artifact itself.

Each cached artifact contains metadata too. This includes information about computed checksums for this artifact
as well as names which were used to refer to the artifact. Metadata is stored in the cache directory too, the
file name is the UUID of the artifact with a ``.yaml`` extension.

Example
    If your artifact will have ``1258069e-7194-426d-a6ab-ade0a27b8290`` UUID assigned with it, then it will be found
    under the ``~/.cekit/cache/1258069e-7194-426d-a6ab-ade0a27b8290`` path and the metadata can be found in the
    ``~/.cekit/cache/1258069e-7194-426d-a6ab-ade0a27b8290.yaml`` file.

Artifacts in cache are **discovered by the hash value**.

While adding an artifact to the cache, CEKit is computing it's checksums for all currently supported algorithms (``md5``,
``sha1``, ``sha256``). This makes it possible to refer the same artifact in descriptors using different algorithms.

This also means that CEKit is using cache only for artifacts which define **at least one hash**.

Automatic caching
------------------

CEKit is automatically caching all artifacts used to build the image. Consider following image descriptor snippet:

.. code-block:: yaml

    artifacts:
        - name: jolokia-1.3.6-bin.tar.gz
          url: https://github.com/rhuss/jolokia/releases/download/v1.3.6/jolokia-1.3.6-bin.tar.gz
          md5: 75e5b5ba0b804cd9def9f20a70af649f

This artifact will be automatically added into the cache during image build. This is useful
as the artifact will be automatically copied from cache instead of downloading it again on any rebuild.

Managing cache
--------------

CEKit provides command line tool called ``cekit-cache`` which is used to manage cache.

It has a ``--work-dir`` (by default set to ``~/.cekit``) parameter which sets CEKit's working directory. This is where the ``cache`` directory will be
located. 

.. warning::

   If you customize ``--work-dir`` -- make sure you use the same path for ``cekit`` and ``cekit-cache`` commands.
   You can also set the path in the :ref:`configuration file <configuration:Working directory>`.

Caching artifacts manually
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

CEKit supports caching artifacts manually. This is very usefull if you need to introduce non-public
artifact to a CEKit. To cache an artifact you need to specify path to the artifact on filesystem or its URL and
**at least one** of the supported hashes (``md5``, ``sha1``, ``sha256``).

Examples
    Caching local artifact

    .. code-block:: bash

        $ cekit-cache add path/to/file --md5 checksum

    Caching remote artifact

    .. code-block:: bash

        $ cekit-cache add https://foo.bar/baz --sha256 checksum

Listing cached artifacts
^^^^^^^^^^^^^^^^^^^^^^^^

To list all artifact known to CEKit cache you need to run following command:

.. code-block:: bash
	  
	  $ cekit-cache ls

After running the command you can see following output:

.. code-block:: yaml

    912c3cc4-7bd3-445d-9927-5063ba3b3bc1:
        sha256: 04b95a87ee88e1cba7682884ea7f89d5ec097c0fa513e7aca1366d79fb3290a8
        sha1: 9cbe5393b6837849edbc067fe1a1405ff0c43605
        md5: f97f623e5b614a7b6d1eb5ff7158027b
        names:
            - hawkular-javaagent-1.0.1.Final-redhat-2-shaded.jar
    7992df2a-be4e-43b5-a02f-18e429ed3ac6:
        sha256: b2cd21075a4c2a3bc04d2595a1a81ad79d6a36774c28608e04cb73ef76da3458
        sha1: 9e26ba61c5665aafc849073edeb769be555283cd
        md5: 080075877a66adf52b7f6d0013fa9730
        names:
            - tomcat.tar.gz

Removing cached artifact
^^^^^^^^^^^^^^^^^^^^^^^^

If you are not interested in particular artifact from cache, you can delete
it by executing following command:

.. code-block:: bash
	  
	  $ cekit-cache rm uuid

.. note::
   You can get uuid of any artifact by invoking ``cekit-cache ls`` command. Please consult :ref:`caching:Listing cached artifacts`.


Wiping cache
^^^^^^^^^^^^^^

To wipe whole artifact cache you need to run the ``cekit-cache clear`` command. This will ask you for confirmation
of the removal step.

.. code-block:: bash

	  $ cekit-cache clear
