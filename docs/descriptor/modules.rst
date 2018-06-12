``modules``
-----------




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

