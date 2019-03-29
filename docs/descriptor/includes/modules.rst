Modules
-------

Key
    ``modules``
Required
    No

The modules section is responsible for defining module repositories and providing the list of modules
to be installed in order. 

.. code-block:: yaml

    modules:
        repositories:
            # Add local modules located next to the image descriptor
            # These modules are specific to the image we build and are not meant
            # to be shared
            - path: modules

            # Add a shared module repository located on GitHub. This repository
            # can contain several modules.
            - git:
                url: https://github.com/cekit/example-common-module.git
                ref: master

        # Install selected modules (in order)
        install:
            - name: jdk8
            - name: user
            - name: tomcat

Module repositories
^^^^^^^^^^^^^^^^^^^

Key
    ``repositories``
Required
    No

Module repositories specify location of modules that are to be incorporated
into the image. These repositories may be ``git`` repositories or directories
on the local file system (``path``). CEKit will scan the repositories for
``module.xml`` files, which are used to encapsulate image details that may be
incorporated into multiple images.

.. code-block:: yaml

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

Key
    ``install``
Required
    No

The ``install`` section is used to define what modules should be installed in the image
in what order. Name used to specify the module is the ``name`` field from the module
descriptor.

.. code-block:: yaml

    modules:
      install:
          - name: xpaas.java
          - name: xpaas.amq.install

You can even request specific module version via *version* key as follows:

.. code-block:: yaml

    modules:
      install:
          - name: xpaas.java
	    version: 1.2-dev
          - name: xpaas.amq.install

