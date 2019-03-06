
.. _artifacts_caching:

Artifact Caching
================

CEKit is automatically caching all artifacts used to build the image. This means that if your image descriptor contains following artifact:

.. code:: yaml

    artifacts:
          # File will be downloaded and verified.
        - name: jolokia-1.3.6-bin.tar.gz
          url: https://github.com/rhuss/jolokia/releases/download/v1.3.6/jolokia-1.3.6-bin.tar.gz
          md5: 75e5b5ba0b804cd9def9f20a70af649f

It will be automatically cached into ``~/.cekit/cache/`` directory during image build. This is useful as the artifact will be automatically copied from cache instead of downloading it again on any rebuild.

.. note::

   Artifacts in cache are discovered by a hash value. So even if you define same artifact by different name it will be discovered in cache and copied into your image. This also means that CEKit is using cache only for artifacts which define at least one hash.



Managing Cache
--------------

CEKit contains command line tool called ``cekit-cache`` which is used to manage its cache.

**Options affecting cekit-cache:**

* ``--verbose`` -- setups verbose output
* ``--work-dir`` -- sets CEKit works directory where cache directory is located. See :ref:`Configuration section for work_dir<workdir_config>`
* ``--version`` -- prints CEKit version

.. note::

   All cache related files are places in your ``--work-dir`` inside ``cache`` subdirectory. This is ``~/.cekit/cache`` by default. This means that
   cache is realted to your ``--work-dir`` and switching your ``--work-dir`` will use different artifact cache.

  

Caching an artifact manually
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
CEKit supports caching an artifact manually. This is very use full if you need to introduce non-public
artifact to a CEKit. To cache an artifact you need to specify path to the artifact on filesystem or its URL and one of the supported hashes (md5, sha256, sha512).

*Example*: Specifying an artifact via path:

.. code:: bash

	  $ cekit-cache add path/to/file --md5 checksum

*Example*: Specifying an artifact via url:

.. code:: bash

	  $ cekit-cache add https://foo.bar/baz --sha256 checksum


**Options affecting cekit-cache add:**

* ``--md5`` -- contains md5 hash of an artifact
* ``--sha256`` -- contains sha256 hash of an artifact
* ``--sha512`` -- contains sha512 hash of an artifact

.. _listing_cached_artifacts:

Listing cached artifacts
^^^^^^^^^^^^^^^^^^^^^^^^
To list all artifact known to a CEKit cache you need to run following command:

.. code:: bash
	  
	  $ cekit-cache ls

After running the command you can see following output:
.. code::

   Cached artifacts:
   912c3cc4-7bd3-445d-9927-5063ba3b3bc1:
     sha256: 04b95a87ee88e1cba7682884ea7f89d5ec097c0fa513e7aca1366d79fb3290a8
     sha1: 9cbe5393b6837849edbc067fe1a1405ff0c43605
     md5: f97f623e5b614a7b6d1eb5ff7158027b
     names:
       hawkular-javaagent-1.0.1.Final-redhat-2-shaded.jar
   d9171217-744e-43af-8d2f-5ee04f2fd741:
     sha256: 223d394c3912028ddd18c6401b3aa97fe80e8d0ae3646df2036d856f35f18735
     sha1: 7c32933edaea4ba40bdcc171e25a0a9c36e2de20
     md5: d31c6b1525e6d2d24062ef26a9f639a8
     names:
      jolokia-jvm-1.5.0.redhat-1-agent.jar

As you can see, we've got listing of two artifacts and they're represented by uuid. One is **912c3cc4-7bd3-445d-9927-5063ba3b3bc1** which is ``hawkular-javaagent-1.0.1.Final-redhat-2-shaded.jar``. Second one is **d9171217-744e-43af-8d2f-5ee04f2fd741** which is ``jolokia-jvm-1.5.0.redhat-1-agent.jar``. The artifacts uuids are auto generated when artifact is cached and serves as an unique id of an artifact.

.. note::
   Artifact uuid is also used as a filename for an artifact, you can see them in your ``~/.cekit/cache`` directory.

Removing cached artifact
^^^^^^^^^^^^^^^^^^^^^^^^
If you are not interested in particular artifact being at your cache you can delete
it by executing following command:

.. code:: bash
	  
	  $ cekit-cache rm uuid


.. note::
   You can get uuid of any artifact by invoking ``cekit-cache ls`` command. Please consult :ref:`listing_cached_artifacts`


Wiping whole cache
^^^^^^^^^^^^^^^^^^
To wipe whole artifact cache you need to manually remove ``cache`` subdirectory inside your ``--work-dir``.

*Example:* To remove your cache located in ``~/.cekit/cache`` directory run:

.. code:: bash

	  $ rm -rf ~/.cekit/cache
