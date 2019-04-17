Summary
=================

**Congratulations! You have now completed the getting started guide.**

The examples used are available at github:

* https://github.com/cekit/example-image-tomcat/
* https://github.com/cekit/example-common-module/

The only difference is that the ``example-image-tomcat`` utilises a remote module repository reference to load the ``jdk8`` and ``user`` modules which are within ``example-common-module`` e.g.

.. code-block:: yaml

  modules:
    repositories:
        - path: modules
        - git:
            url: https://github.com/cekit/example-common-module.git
            ref: master
