Artifacts
---------

It's common for images to require external artifacts like jar files, installers, etc.
In most cases you will want to add files into the image and use them during  image build process.

Artifacts section is meant exactly for this. *Cekit will automatically
fetch any artifacts* specified in this section and check their consistency by computing checksum of
the downloaded file and comparing it with the desired value. Currently supported algorithms are: md5, sha1 and sha256. If no algorithm is provided, artifact will  be fetched **every** time.

All artifacts are automatically cached during an image build. To learn more about cache please take a look at :ref:`artifacts_caching`


The output name for downloaded resources will match the ``target`` attribute, which defaults to
the base name of the file/URL. 



.. note:: 

   For artifacts that are not publicly available Cekit provides a way to
   add a description detailing a location from which the artifact can be obtained.

   .. code:: yaml

      artifacts:
        - path: jboss-eap-6.4.0.zip
          md5: 9a5d37631919a111ddf42ceda1a9f0b5
          description: "Red Hat JBoss EAP 6.4.0 distribution available on Customer Portal: https://access.redhat.com/jbossnetwork/restricted/softwareDetail.html?softwareId=37393&product=appplatform&version=6.4&downloadType=distributions"

   If Cekit is not able to download an artifact and this artifact has a ``description`` defined -- the build
   will fail but a message with the description will be printed together with information on where to place
   the manually downloaded artifact.



Plain
^^^^^

This is the easiest way of defining an artifact. You are just specifying its name and **md5** checksum.
This approach relies on :ref:`artifacts_caching` to provide the artifact in cache. This section should be used to show that a particular artifact is needed for the image but its not publicly available.

.. code:: yaml 

    artifacts:
        - name: jolokia-1.3.6-bin.tar.gz
          md5: 75e5b5ba0b804cd9def9f20a70af649f
          target: jolokia.jar

.. note::

   See :ref:`Red Hat Environment<redhat_env>` for a description how Plain Artifacts are affected by Red
   Hat switch.

          
URL
^^^

This way of defining repository ask Cekit to download and artifact from a specified URL.


.. code:: yaml

    artifacts:
        - name: jolokia-1.3.6-bin.tar.gz
          url: https://github.com/rhuss/jolokia/releases/download/v1.3.6/jolokia-1.3.6-bin.tar.gz
          md5: 75e5b5ba0b804cd9def9f20a70af649f




Path
^^^^

This way of defining artifact is mostly used in development overrides and enables you to inject
an artifact from a local filesystem.

.. code:: yaml

    artifacts:
        - name: jolokia-1.3.6-bin.tar.gz
          path: local-artifacts/jolokia-1.3.6-bin.tar.gz
          md5: 75e5b5ba0b804cd9def9f20a70af649f

.. note::

   If you are using relative ``path`` to define an artifact, path is considered relative to an
   image descriptor which introduced that artifact.
   
   **Example**: If an artifact is defined inside */foo/bar/image.yaml* with a path: *baz/1.zip*
   the artifact will be resolved as */foo/bar/baz/1.zip*





