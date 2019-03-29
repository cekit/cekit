Local development
==========================


CEKit enables you to use a work in progress modules to build the image by exploiting
its overrides system. As an example, imagine we have very simple image which is using
one module from a remote Git repository, like this:

.. code-block:: yaml

    schema_version: 1

    name: cekit/example-jdk8
    version: 1.0
    from: centos:7
    description: "JDK 8 image"

    modules:
      repositories:
        # Add a shared module repository located on GitHub. This repository
        # can contain several modules.
        - git:
            url: https://github.com/cekit/example-common-module.git
            ref: master

    # Install selected modules (in order)
    install:
      - name: jdk8
      - name: user

Now imagine, we have found a bug in its ``jd8`` module. We will clone the module
repository locally by executing:

1. Clone ``cct_module`` to your workstation to ``~/repo/cct_module``

.. code-block:: bash

  $ git clone https://github.com/cekit/example-common-module.git ~/repos/example-common-module

2. Then we will create ``override.yaml`` file next to the ``image.yaml``. Override.yaml should look like this:

.. code-block:: yaml

  schema_version: 1
  modules:
    repositories:
      - path: "/home/user/repo/cct_module"

3. We now can build the image using overridden module by executing:

.. code:: bash

  $ cekit generate --overrides-file overrides.yaml

4. When your work is finished, commit and push your changes to a module repository and remove overrides.yaml

Injecting local artifacts
----------------------------

During module/image development there can be a need to use locally built artifact instead of a released one. The easiest way to inject
such artifact is to use override mechanism.


To override an artifact imagine, that you have an artifact defined in a way:

.. code:: yaml

          - md5: d31c6b1525e6d2d24062ef26a9f639a8
            name: jolokia.jar
            url: https://maven.repository.redhat.com/ga/org/jolokia/jolokia-jvm/1.5.0.redhat-1/jolokia-jvm-1.5.0.redhat-1-agent.jar

And you want to inject a local build of new version of our artifact. To archive it you need to create following override:

.. code:: yaml

          - name: jolokia.jar
            path: /tmp/build/jolokia.jar

Whenever you override artifact, all previous checksums are removed too. If you want your new artifact to pass integrity checks you need to define checksum also in overrides in a following way:

.. code:: yaml

          - md5: d31c6b1525e6d2d24062ef26a9f639a8
            name: jolokia.jar
            path: /tmp/build/joloika.jar

.. note::
   If the artifacts lacks the name key, its automatically created by using basename of the artifact path or url.
