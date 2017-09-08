Image descriptor file
=====================

Most important, user facing part of Concreate is the descriptor file. We use
`YAML <http://yaml.org/>`_ format which is easy to read and edit by humans but still machine
parseable.

.. note::

    By convention we use the ``image.yaml``  file name for the image descriptor.

Below you can find description of image descriptor sections.

``name``
--------

This key is **required**.

Image name without the registry part.

.. code:: yaml

    name: "jboss-eap-7/eap70-openshift"

``version``
-----------

This key is **required**.

Version of the image.

.. code:: yaml

    version: "1.4"

``from``
--------

This key is **required**.

Base image of your image.

.. code:: yaml

    from: "jboss-eap-7-tech-preview/eap70:1.2"

``schema_version``
------------------

This key is **required**.

Here you specify the schema version of the descriptor. This influences what versions of Concreate are able to parse it.

.. code:: yaml

    schema_version: 1

``description``
---------------

Short summary of the image.

Value of the ``description`` key is added to the image as two labels: ``description``
and ``summary`` unless such labels are already defined in the image descriptor's
:ref:`labels` section.

.. code:: yaml

    description: "Red Hat JBoss Enterprise Application 7.0 - An application platform for hosting your apps that provides an innovative modular, cloud-ready architecture, powerful management and automation, and world class developer productivity."

``user``
--------

The user that should be used to launch the main process in the container. Can be name or uid. See `OCI spec <https://github.com/opencontainers/image-spec/blob/master/config.md#properties>`_ for more information.

.. code:: yaml

    user: "alice"

.. _labels:

``labels``
----------

.. note::

    Learn more about `standard labels in container images <https://github.com/projectatomic/ContainerApplicationGenericLabels>`_.

Every image can include labels. Concreate makes it easy to do so with the ``labels`` section.

.. code:: yaml

    labels:
        - name: "io.k8s.description"
          value: "Platform for building and running JavaEE applications on JBoss EAP 7.0"
        - name: "io.k8s.display-name"
          value: "JBoss EAP 7.0"

``envs``
----------

Similar to labels -- we can specify environment variables that should be
present in the container after running the image. We provide ``envs``
section for this.

Environment variables can be divided into two types:

1. **Information environment variables** -- these are set and available in
   the image. This type of environment variables provide information to
   the image consumer. In most cases such environment variables *should not*
   be modified.

2. **Configuration environment variables** -- this type of variables are
   used to define environment variables used to configure services inside
   running container.

   These environment variables are **not** set during image build time but *can* be set at run time.

   Every configuration enviromnent variable should provide an example usage
   (``example``) and short description (``description``).

Please note that you could have an environment variable with both: a ``value``
and ``example`` set. This suggest that this environment variable could be redefined.

.. note::

    Configuration environment variables (without ``value``) are not
    generated to the build source. These can be used instead as a
    source for generating documentation.

.. code:: yaml

    envs:
        - name: "STI_BUILDER"
          value: "jee"
        - name: "JBOSS_MODULES_SYSTEM_PKGS"
          value: "org.jboss.logmanager,jdk.nashorn.api"
        - name: "OPENSHIFT_KUBE_PING_NAMESPACE"
          example: "myproject"
          description: "Clustering project namespace."
        - name: "OPENSHIFT_KUBE_PING_LABELS"
          example: "application=eap-app"
          description: "Clustering labels selector."

``ports``
---------

This section is used to mark which ports should be exposed in the
container. If we want to highlight a port used in the container, but not necessary expose
it -- we should set the ``expose`` flag to ``false`` (``true`` by default).

.. code:: yaml

    ports:
        - value: 8443
        - value: 8778
          expose: false

``workdir``
-----------

Sets the current working directory of the entrypoint process in the container.

.. code:: yaml

    workdir: "/home/jboss"

``user``
--------

Specifies the user (can be username or uid) that should be used to launch the entrypoint
process.

.. code:: yaml

    user: "alice"

``cmd``
-------
``entrypoint``
--------------

You can specify the entrypoint or command that should be used by the
container with the ``cmd`` and ``entrypoint``.

.. note::

    Both ``entrypoint`` and ``cmd`` keys use the array form of
    providing its value.

.. code:: yaml

    entrypoint:
        - "/opt/eap/bin/wrapper.sh"
    cmd:
        - "some cmd"
        - "argument"

``packages``
------------

If you need to install additional packages you can use the ``packages``
section where you specify package names to be installed.

.. todo::

    Adding repo files

.. code:: yaml

    packages:
        - mongodb24-mongo-java-driver
        - postgresql-jdbc
        - mysql-connector-java
        - maven
        - hostname

``artifacts``
-------------

It's common for images to require external artifacts.
In most cases you will want to add files into the image and use them at
the image build process.

Artifacts section is meant exactly for this. *Concreate will automatically
fetch any artifacts* specified in this section
and check their consistency by comptuting checksum of
the downloaded file and comparing it with the desired value.

.. code:: yaml

    artifacts:
        - artifact: https://github.com/rhuss/jolokia/releases/download/v1.3.6/jolokia-1.3.6-bin.tar.gz
          md5: 75e5b5ba0b804cd9def9f20a70af649f

.. note::

    Currently supported algorithms are: md5, sha1 and sha256.

For artifacts that are not publicly available Concreate provides a way to
add a hint from there such artifact could be downloaded.

.. code:: yaml

    artifacts:
        - artifact: jboss-eap-6.4.0.zip
          md5: 9a5d37631919a111ddf42ceda1a9f0b5
          hint: "Artifact is available on Customer Portal: https://access.redhat.com/jbossnetwork/restricted/softwareDetail.html?softwareId=37393&product=appplatform&version=6.4&downloadType=distributions"

If Concreate is not able to download an artifact and this artifacts has a ``hint`` defined -- the build
will be failed but a message with the defined hint will be printed together with information where to place
the manually downloaded artifact.

``volumes``
-----------

In case you want to define volumes for your image, just use the ``volumes`` section!

.. code:: yaml

    volumes:
        - "/opt/eap/standalone"

``dependencies``
----------------

.. todo::

    Write this section


``modules``
-----------

Modules are discussed in details :ref:`here <modules>`.

