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
``sha1``, ``sha256``, ``sha512``). This makes it possible to refer the same artifact in descriptors using different algorithms.

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
   You can also set the path in the :ref:`configuration file <handbook/configuration:Working directory>`.

Caching artifacts manually
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

CEKit supports caching artifacts manually. This is very usefull if you need to introduce non-public
artifact to a CEKit. To cache an artifact you need to specify path to the artifact on filesystem or its URL and
**at least one** of the supported hashes (``md5``, ``sha1``, ``sha256``, ``sha512``).

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

    eba0b8ce-9562-439f-8a56-b9703063a9a3:
      sha512: 5f4184e0fe7e5c8ae67f5e6bc5deee881051cc712e9ff8aeddf3529724c00e402c94bb75561dd9517a372f06c1fcb78dc7ae65dcbd4c156b3ba4d8e267ec2936
      sha256: c93c096c8d64062345b26b34c85127a6848cff95a4bb829333a06b83222a5cfa
      sha1: 3c3231e51248cb76ec97214f6224563d074111c1
      md5: c1a230474c21335c983f45e84dcf8fb9
      names:
        - spark-2.4.0-bin-hadoop2.7.tgz

    dba5a813-3972-4dcf-92a4-87049357f7e0:
      sha512: cf83e1357eefb8bdf1542850d66d8007d620e4050b5715dc83f4a921d36ce9ce47d0d13c5d85f2b0ff8318d2877eec2f63b931bd47417a81a538327af927da3e
      sha256: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
      sha1: da39a3ee5e6b4b0d3255bfef95601890afd80709
      md5: d41d8cd98f00b204e9800998ecf8427e
      names:
        - artifact


Removing cached artifact
^^^^^^^^^^^^^^^^^^^^^^^^

If you are not interested in particular artifact from cache, you can delete
it by executing following command:

.. code-block:: bash
	  
	  $ cekit-cache rm uuid

.. note::
   You can get uuid of any artifact by invoking ``cekit-cache ls`` command. Please consult :ref:`handbook/caching:Listing cached artifacts`.


Wiping cache
^^^^^^^^^^^^^^

To wipe whole artifact cache you need to run the ``cekit-cache clear`` command. This will ask you for confirmation
of the removal step.

.. code-block:: bash

	  $ cekit-cache clear
