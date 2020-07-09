Artifacts
---------

It's common for images to require external artifacts like jar files, installers, etc.
In most cases you will want to add some files into the image and use them during image build process.

Artifacts section is meant exactly for this. CEKit will try to *automatically*
fetch any artifacts specified in this section.

If for some reason automatic fetching of artifacts is not an option for you,
you should define artifacts as plain artifacts and use the ``cekit-cache``
command to add the artifact to local cache, making it available for the build
process automatically. See :doc:`/handbook/caching` chapter.

Artifact features
^^^^^^^^^^^^^^^^^^^^

Checksums
    Almost all artifacts will be checked for consistency by computing checksum of
    the fetched file and comparing it with the desired value. Currently supported algorithms
    are: ``md5``, ``sha1``, ``sha256`` and ``sha512``.

    You can define multiple checksums for a single artifact. All specified checksums will
    be validated.

    If no algorithm is provided, artifacts will be fetched **every time**.

    This can be useful when building images with snapshot content. In this case you are not
    concerned about the consistency but rather focusing on rapid
    development. We advice that you define checksum when your content becomes stable.

Caching
    All artifacts are automatically cached during an image build. To learn more about caching please
    take a look at :doc:`/handbook//caching` chapter.


Common artifact keys
^^^^^^^^^^^^^^^^^^^^

``name``
    Used to define unique identifier of the artifact.

    The ``name`` key is very important. It's role is to provide a unique identifier for the artifact.
    If it's not provided, it will be computed from the resource definition, but we **strongly suggest**
    to provide the ``name`` keys always.

    Value of this key does not need to be a filename, because it's just an identifier used
    to refer the artifact. Using meaningful and unique identifiers is important in case when
    you want to use :doc:`/handbook/overrides`. It will make it much easier to refer the artifact
    and thus override it.

``target``
    The output name for fetched resources will match the ``target`` attribute. If it is not defined
    then base name of the ``name`` attribute will be used. If it's not provided either then base name
    of the path/URL will be used.

    Below you can find a few examples.

        .. code-block:: yaml

            artifacts:
                - name: jboss-eap-distribution
                  path: jboss-eap-6.4.0.zip
                  target: jboss-eap.zip

        Target file name: ``jboss-eap.zip``.

        .. code-block:: yaml

            artifacts:
                - name: jboss-eap-distribution
                  path: jboss-eap-6.4.0.zip

        Target file name: ``jboss-eap-distribution``.

        .. code-block:: yaml

            artifacts:
                - path: jboss-eap-6.4.0.zip

        Target file name: ``jboss-eap-6.4.0.zip``.

``dest``
    The ``dest`` key defines the destination directory where the particular artifact will be placed within
    the container image. By default it is set to ``/tmp/artifacts/``.

    The ``dest`` key specifies the **directory** path, to control **file name**, use ``target`` key
    as explained above. In order to get maximum control over the target artifact naming,
    you should use both ``dest`` and ``target`` together.

    Examples:

        .. code-block:: yaml

            artifacts:
                - name: jboss-eap-distribution
                    path: jboss-eap-6.4.0.zip
                    target: jboss-eap.zip

        Target file path is: ``/tmp/artifacts/jboss-eap.zip``.

        .. code-block:: yaml

            artifacts:
                - name: jboss-eap-distribution
                    path: jboss-eap-6.4.0.zip
                    target: jboss-eap.zip
                    dest: /opt

        Target file path is: ``/opt/jboss-eap.zip``.

    .. note::
        The default temporary directory (``/tmp/artifacts/``) will be cleaned up automatically
        after the build process is done meaning that artifacts are available only at the build time.

        Artifacts using custom ``dest`` values are not affected.

``description``
   Describes the artifact. This is an optional key that can be used to add more information
   about the artifact.

   Adding description to artifacts makes it much easier to understand what artifact
   it is just by looking at the image/module descriptor.

   .. code-block:: yaml

      artifacts:
        - path: jboss-eap-6.4.0.zip
          md5: 9a5d37631919a111ddf42ceda1a9f0b5
          description: "Red Hat JBoss EAP 6.4.0 distribution available on Customer Portal: https://access.redhat.com/jbossnetwork/restricted/softwareDetail.html?softwareId=37393&product=appplatform&version=6.4&downloadType=distributions"

   If CEKit is not able to download an artifact and this artifact has a ``description`` defined -- the build
   will fail but a message with the description will be printed together with information on where to place
   the manually downloaded artifact so that the build could be resumed.

Artifact types
^^^^^^^^^^^^^^^^^^^^

CEKit supports following artifact types:

* Plain artifacts
* URL artifacts
* Path artifacts
* Image source artifacts

Plain artifacts
******************

This is an abstract way of defining artifacts. The only required keys are ``name`` and the ``md5`` checksum.
This type of artifacts is used to define artifacts that are not available publicly and instead
provided by some (internal) systems.

.. schema:: cekit.descriptor.resource._PlainResource
    :name: plain-artifact-schema

.. code-block:: yaml
    :name: plain-artifact-examples
    :caption: Examples

    artifacts:
        - name: jolokia
          md5: 75e5b5ba0b804cd9def9f20a70af649f
          target: jolokia.tar.gz

As you can see, the definition does not define from where the artifact should be fetched.
This approach relies on :doc:`/handbook/caching` to provide the artifact.

.. note::

   See :doc:`/handbook/redhat` for description how plain artifacts are used in the
   Red Hat environment.

URL artifacts
******************

This is the simplest way of defining artifacts. You need to provide the ``url`` key which is the URL from where the
artifact should be fetched from.

.. schema:: cekit.descriptor.resource._UrlResource
    :name: url-artifact-schema

.. tip::
    You should always specify at least one checksum to make sure the downloaded artifact is correct.

.. code-block:: yaml
    :name: url-artifact-examples
    :caption: Examples

    artifacts:
        - name: "jolokia"
          url: "https://github.com/rhuss/jolokia/releases/download/v1.3.6/jolokia-1.3.6-bin.tar.gz"
          # The md5 checksum of the artifact
          md5: "75e5b5ba0b804cd9def9f20a70af649f"

        - name: "jolokia"
          url: "https://github.com/rhuss/jolokia/releases/download/v1.3.6/jolokia-1.3.6-bin.tar.gz"
          # Free text description of the artifact
          description: "Library required to access server data via JMX"
          md5: "75e5b5ba0b804cd9def9f20a70af649f"
          # Final name of the downloaded artifact
          target: "jolokia.tar.gz"

Path artifacts
******************

This way of defining artifacts is mostly used in development :doc:`overrides </handbook/overrides>`
and enables you to inject artifacts from a local filesystem.

.. schema:: cekit.descriptor.resource._PathResource
    :name: path-artifact-schema

.. tip::
    You should always specify at least one checksum to make sure the artifact is correct.

.. code-block:: yaml
    :name: path-artifact-examples
    :caption: Examples

    artifacts:
        - name: jolokia-1.3.6-bin.tar.gz
          path: local-artifacts/jolokia-1.3.6-bin.tar.gz
          md5: 75e5b5ba0b804cd9def9f20a70af649f

.. note::

    If you are using relative ``path`` to define an artifact, path is considered relative to an
    image descriptor which introduced that artifact.

    Example
        If an artifact is defined inside ``/foo/bar/image.yaml`` with a path: ``baz/1.zip``
        the artifact will be resolved as ``/foo/bar/baz/1.zip``

Image source artifacts
************************

Image source artifacts are used in :doc:`multi-stage builds </handbook/multi-stage>`.
With image source artifacts you can define files built in previous stages of the
multi-stage builds.

.. schema:: cekit.descriptor.resource._ImageContentResource
    :name: image-source-artifact-schema

.. note::
   Please note that image source artifacts do not allow for defining checksums due to the nature of this type of artifact.

.. code-block:: yaml
    :name: image-source-artifact-examples
    :caption: Examples

    artifacts:
        - name: application
          # Name of the image (stage) from where we will fetch the artifact
          image: builder
          # Path to the artifact within the image
          path: /path/to/application/inside/the/builder/image.jar

