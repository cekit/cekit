.. _image_descriptor:

Image descriptor file
=====================

Most important, user facing part of Cekit is the descriptor file. We use
`YAML <http://yaml.org/>`_ format which is easy to read and edit by humans but still machine
parseable.

.. note::

    By convention we use the ``image.yaml``  file name for the image descriptor.

Below you can find description of image descriptor sections.

``artifacts``
-------------

It's common for images to require external artifacts.
In most cases you will want to add files into the image and use them at
the image build process.

Artifacts section is meant exactly for this. *Cekit will automatically
fetch any artifacts* specified in this section
and check their consistency by computing checksum of
the downloaded file and comparing it with the desired value. The output name
for downloaded resources will match the ``name`` attribute, which defaults to
the base name of the file/URL. Artifact locations may be specified as ``url``\s,
``path``\s or ``git`` references.

.. note::

   If you are using relative ``path`` to define an artifact, path is considered relative to an
   image descriptor which introduced that artifact.
   
   **Example**: If an artifact is defined inside */foo/bar/image.yaml* with a path: *baz/1.zip*
   the artifact will be resolved as */foo/bar/baz/1.zip*

.. code:: yaml

    artifacts:
          # File will be downloaded and verified.
        - name: jolokia-1.3.6-bin.tar.gz
          url: https://github.com/rhuss/jolokia/releases/download/v1.3.6/jolokia-1.3.6-bin.tar.gz
          md5: 75e5b5ba0b804cd9def9f20a70af649f

          # File exists on local machine relative to this file. Checksum will be verified.
          # The "name" attribute defaults to: "hawkular-javaagent-1.0.0.CR4-redhat-1-shaded.jar"
        - path: local-artifacts/hawkular-javaagent-1.0.0.CR4-redhat-1-shaded.jar
          md5: e133776c76a474ed46ac88c856eabe34

          # git project will be cloned
          # "name" attribute defaults to "project"
        - git:
              url: https://github.com/organization/project
              ref: master

.. note::

    Currently supported algorithms are: md5, sha1 and sha256. If no algorithm is provided, artifact will
    be fetched **every** time.

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

``description``
---------------

Short summary of the image.

Value of the ``description`` key is added to the image as two labels: ``description``
and ``summary`` unless such labels are already defined in the image descriptor's
:ref:`labels` section.

.. code:: yaml

    description: "Red Hat JBoss Enterprise Application 7.0 - An application platform for hosting your apps that provides an innovative modular, cloud-ready architecture, powerful management and automation, and world class developer productivity."

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

``from``
--------

This key is **required**.

Base image of your image.

.. code:: yaml

    from: "jboss-eap-7-tech-preview/eap70:1.2"

.. _labels:

``labels``
----------

.. note::

    Learn more about `standard labels in container images <https://github.com/projectatomic/ContainerApplicationGenericLabels>`_.

Every image can include labels. Cekit makes it easy to do so with the ``labels`` section.

.. code:: yaml

    labels:
        - name: "io.k8s.description"
          value: "Platform for building and running JavaEE applications on JBoss EAP 7.0"
        - name: "io.k8s.display-name"
          value: "JBoss EAP 7.0"

``modules``
-----------

.. note::

    Modules are discussed in details :ref:`here <modules>`.

Module repositories
^^^^^^^^^^^^^^^^^^^

Module repositories specify location of modules that are to be incorporated
into the image. These repositories may be ``git`` repositories or directories
on the local file system (``path``). Cekit will scan the repositories for
``module.xml`` files, which are used to encapsulate image details that may be
incorporated into multiple images.

.. code:: yaml

    modules:
      repositories:
          # Modules pulled from Java image project on GitHub
        - git:
              url: https://github.com/jboss-container-images/redhat-openjdk-18-openshift-image
              ref: 1.0

          # Modules pulled locally from "custom-modules" directory, collocated with image descriptor
        - path: custom-modules

Module installation
^^^^^^^^^^^^^^^^^^^

The ``install`` section is used to define what modules should be installed in the image
in what order. Name used to specify the module is the ``name`` field from the module
descriptor.

.. code:: yaml

    modules:
      install:
          - name: xpaas.java
          - name: xpaas.amq.install

You can even request specific module version via *version* key as follows:

.. code:: yaml

    modules:
      install:
          - name: xpaas.java
	    version: 1.2-dev
          - name: xpaas.amq.install

``name``
--------

This key is **required**.

Image name without the registry part.

.. code:: yaml

    name: "jboss-eap-7/eap70-openshift"

.. _descriptor_packages:

``packages``
------------

To install additional RPM packages you can use the ``packages``
section where you specify package names and repositories to be used.

.. code:: yaml

    packages:
        install:
            - mongodb24-mongo-java-driver
            - postgresql-jdbc
            - mysql-connector-java
            - maven
            - hostname

Packages are defined in the ``install`` subsection.

``repositories``
----------------
Cekit uses all repositories configured inside the image. You can also specify additional
repositories inside the repositories subsection. Cekit currently supports three ways of defining
additional repositories:

``RPM``
^^^^^^^^
This is way is using RPM existing in yum repositories to enable new repository.

**Example**: To enable `CentOS SCL <https://wiki.centos.org/AdditionalResources/Repositories/SCL>`_ inside the
image you should define repository in a following way:

.. code:: yaml

    packages:
        repositories:
            - name: scl
	      rpm: centos-release-scl


``ODCS``
^^^^^^^^^
This way is instructs `ODCS <https://pagure.io/odcs>`_ to generate on demand pulp repositories.
To use ODCS define repository section in following way:

.. code:: yaml

    packages:
        repositories:
            - name: foo
	      odcs:
	        pulp: rhel-7-extras-rpm
		
*note*: See :ref:`ODCS configuration section <odcs_config>` for additonal details.


``URL``
^^^^^^^^
This approach enables you to download a yum repository file and corresponding GPG key. To do it, define
repositories section in a way of:

.. code:: yaml

    packages:
        repositories:
            - name: foo
	      url:
	        repository: https://web.example/foo.repo
                gpg: https://web.exmaple/foo.gpg

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

``run``
-------

The ``run`` section encapsulates instructions related to launching main process
in the container including: ``cmd``, ``entrypoint``, ``user`` and ``workdir``.
All subsections are described later in this paragraph.

Below you can find full example that uses every possible option.

.. code:: yaml

    run:
        cmd:
            - "argument1"
            - "argument2"
        entrypoint:
            - "/opt/eap/bin/wrapper.sh"
        user: "alice"
        workdir: "/home/jboss"


``cmd``
^^^^^^^

Command that should be executed by the container at run time.

.. code:: yaml

    run:
        cmd:
            - "some cmd"
            - "argument"

``entrypoint``
^^^^^^^^^^^^^^

Entrypoint that should be executed by the container at run time.

.. code:: yaml

    run:
        entrypoint:
            - "/opt/eap/bin/wrapper.sh"

``user``
^^^^^^^^

Specifies the user (can be username or uid) that should be used to launch the entrypoint
process.

.. code:: yaml

    run:
        user: "alice"

``workdir``
^^^^^^^^^^^

Sets the current working directory of the entrypoint process in the container.

.. code:: yaml

    run:
        workdir: "/home/jboss"

``schema_version``
------------------

This key is **required**.

Here you specify the schema version of the descriptor. This influences what versions of Cekit are able to parse it.

.. code:: yaml

    schema_version: 1

``version``
-----------

This key is **required**.

Version of the image.

.. code:: yaml

    version: "1.4"

``volumes``
-----------

In case you want to define volumes for your image, just use the ``volumes`` section!

.. code:: yaml

    volumes:
        - name: "volume.eap"
          path: "/opt/eap/standalone"

.. note::

    The ``name`` key is optional. If not specified the value of ``path`` key will be used.


