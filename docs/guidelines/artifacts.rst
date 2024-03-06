Artifact guidelines
==========================


Building container images without content doesn't make sense. You can add :ref:`packages <descriptor/image:Packages>`
shipped with the operating system, you can add scripts with :doc:`modules </handbook/modules/index>`, but
sooner or later you will need to add some bigger (potentially binary) files to your image. Using
:ref:`artifacts <descriptor/image:Artifacts>` is how we handle it in CEKit.

This section helps you define artifacts in your descriptors.

Artifact descriptor
--------------------

There are many :ref:`artifact types available <descriptor/image:Artifact types>`. Please refer to that
page on what is the usage of these.

Below you can find best practices related to defining artifacts.

Proper ``name`` key usage
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: yaml
    :emphasize-lines: 2

    artifacts:
        - name: jolokia
          url: https://github.com/rhuss/jolokia/releases/download/v1.3.6/jolokia-1.3.6-bin.tar.gz
          md5: 75e5b5ba0b804cd9def9f20a70af649f
          description: "Jolokia is remote JMX with JSON over HTTP"

It is very important to use the ``name`` key properly. In CEKit we use ``name`` keys as identifiers
and this is what the artifact's ``name`` key should be -- it should **define a unique key** for the
artifact across the whole image. This is especially important when you define artifacts in modules
that are reused in many images.

The ``name`` key should be generic enough and be descriptive at the same time.

Basing on the example above **bad examples** could be:

    ``jolokia-1.3.6-bin.tar.gz``:
        We should not use the artifact file name as the identifier.
    ``1.3.6``:
        There is no information about the artifact, just version is presented.

**Better** but not ideal is this:

    ``jolokia-1.3.6``:
        Defines what it is and adds full version. Adding exact version may be an overkill. Imagine
        that later we would like to override it with some different version, then the artifact
        ``jolokia-1.3.6`` could point to a ``jolokia-1.6.0-bin.tar.gz`` which would be very misleading.
        We should **avoid** specifying versions.

But the **best option** would be to use something like this:

    ``jolokia_tar``:
        In this case we define what artifact we plan to add and the type of it. We do not specify
        version at all here.

    ``jolokia``:
        This is another possibility, where we use just the common *name* of the artifact. This makes
        it very easy to override and is easy to memoize too.

.. hint::
    When you define the ``name`` for the artifact, make sure you define the ``target`` key too.
    If you don't do this, the **target file name is defaulted to the value of the name key** which may
    be misleading in some cases. See :ref:`this section <descriptor/image:Common artifact keys>`
    for more information on this topic.

Define checksums
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. note::
    :ref:`Learn more about checksums <descriptor/image:Artifact features>`.

.. code-block:: yaml
    :emphasize-lines: 4

    artifacts:
        - name: jolokia
          url: https://github.com/rhuss/jolokia/releases/download/v1.3.6/jolokia-1.3.6-bin.tar.gz
          md5: 75e5b5ba0b804cd9def9f20a70af649f
          description: "Jolokia is remote JMX with JSON over HTTP"

Every artifact should have defined checksums. This will ensure that the fetched artifact's integrity
is preserved. If you do not define them artifacts will be always fetched again. This is good when
the artifact changes very often at the development time, but once you settle on a version,
specify the checksum too.

Add descriptions
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: yaml
    :emphasize-lines: 5

    artifacts:
        - name: jolokia
          url: https://github.com/rhuss/jolokia/releases/download/v1.3.6/jolokia-1.3.6-bin.tar.gz
          md5: 75e5b5ba0b804cd9def9f20a70af649f
          description: "Jolokia is remote JMX with JSON over HTTP"

It's a very good idea to add descriptions to the artifacts. This makes it much easier to understand what
the artifact is about. Besides this, descriptions are used when automatic fetching of artifact is not
possible and is a hint to the developer where to fetch the artifact from manually.

Descriptions can be used also by tools that process image descriptors to produce documentation.
