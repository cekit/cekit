First modules
============================

As described in the :doc:`module reference </descriptor/module>` modules are used as libraries or shared building blocks across images.

To add a module, the ``image.yaml`` file must be modified to add a modules section. This is responsible for defining module repositories and providing the list of modules to be installed in order.

Edit the file to add the following

.. code-block:: yaml

  modules:
    repositories:
        - path: modules
        - git:
            url: https://github.com/cekit/example-common-module.git
            ref: master

This section adds two different types of module repositories that can be incorporated into the image. One is a remote (the ``git`` link) and one is a local filesystem reference. In order to actually select components from the above repositories it is necessary to add an ``install`` section:

.. code-block:: yaml

    # Install selected modules (in order)
    install:
        - name: jdk8
        - name: user

At this point the image will contain the modules from the remote repository. In order to add a local file system module following the below instructions.

1. First, add the following module to the previous list:

   .. code-block:: yaml

        - name: tomcat

2. Create the directory tree ``modules/tomcat`` next to your yaml file.

3. Create the following two files inside the ``tomcat`` directory:

   .. code-block:: sh
      :caption: install.sh

         #!/bin/sh
         set -e
         tar -C /home/user -xf /tmp/artifacts/tomcat.tar.gz
         chown user:user -R /home/user

   .. code-block:: yaml
      :caption: module.yml

         schema_version: 1
         name: tomcat
         version: 1.0
         description: "Module used to install Tomcat 8"
         # Defined artifacts that are used to build the image
         artifacts:
         - name: tomcat.tar.gz
           url: https://archive.apache.org/dist/tomcat/tomcat-8/v8.5.24/bin/apache-tomcat-8.5.24.tar.gz
           md5: 080075877a66adf52b7f6d0013fa9730
           execute:
           - script: install.sh
             run:
             cmd:
             - "/home/user/apache-tomcat-8.5.24/bin/catalina.sh"
               - "run"

Move onto :doc:`module reference </descriptor/build>` to build this new image.
