First modules
============================

As described in the :doc:`module reference </descriptor/module>` modules are used as libraries or shared building blocks across images.

To add a module, the ``image.yaml`` file must be modified to add a modules section. This is responsible for defining module repositories and providing the list of modules to be installed in order. Modules may come from the local file system or from remote git based repositories e.g. on github.

Edit the file to add the highlighted section below.

.. code-block:: yaml
  :emphasize-lines: 5-8

  name: my-example
  version: 1.0
  from: centos:7
  description: My Example Image

  modules:
    repositories:
        - path: modules

As per the below diagram a number of directories must be created next to ``image.yaml``.

.. graphviz::
    :align: center
    :alt: CEKit simple build process diagram

    digraph modules_diagram {
        rankdir="LR";
        graph [fontsize="11", fontname="Open Sans", compound="true", splines=ortho];
        node [shape="box", fontname="Open Sans", fontsize="11"];

        subgraph cluster_0 {
            node [style="filled"];
            penwidth = "2";
            color="dimgrey";
            rank=same;

            modules [label="modules", group="m"];
            jdk8 [label="jdk8"];
            user [label="user"];
            tomcat [label="tomcat", group="m"];
        }
        modules -> tomcat[lhead=cluster_0, arrowhead=none]
        modules -> jdk8[lhead=cluster_0, arrowhead=none]
        modules -> user[lhead=cluster_0, arrowhead=none]
        descriptor [label="image.yaml"];
    }

Once the modules subdirectory and the respective module directories below that have been created they can be added to the image. In order to select a module component from a repository it is necessary to add an ``install`` section as per the highlighted section below.

.. code-block:: yaml
  :emphasize-lines: 6-9

  modules:
    repositories:
        - path: modules

    # Install selected modules (in order)
    install:
        - name: jdk8
        - name: user
        - name: tomcat

In order to add and populate the local file system modules follow the below instructions.

.. note::
   All module yaml files should be named ``module.yaml``

JDK8
^^^^^^^^^
* Create an empty ``module.yaml`` file within the ``jdk8`` directory.
* Enter the following code:

.. code-block:: yaml
   :caption: module.yaml

   schema_version: 1

   name: jdk8
   version: 1.0
   description: Module installing OpenJDK 8

   envs:
      - name: "JAVA_HOME"
        value: "/usr/lib/jvm/java-1.8.0-openjdk"

   packages:
      install:
         - java-1.8.0-openjdk-devel

* An :doc:`environment variable</descriptor/includes/envs>` has been defined that will be present in the container after running the image.
* :doc:`packages</descriptor/includes/packages>` have been used to add the JDK RPM.


User
^^^^^^^^^
* Create the ``module.yaml`` and ``create.sh`` files within the ``user`` directory.
* Enter the following code:

.. code-block:: yaml
   :caption: module.yaml

   schema_version: 1

   name: user
   version: 1.0
   description: "Creates a regular user that could be used to run any service, gui/uid: 1000"

   execute:
     - script: create.sh

   run:
      user: 1000
      workdir: "/home/user"


.. code-block:: sh
   :caption: create.sh

   #!/bin/sh

   set -e

   groupadd -r user -g 1000 && useradd -u 1000 -r -g user -m -d /home/user -s /sbin/nologin -c "Regular user" user


* An :doc:`execute</descriptor/includes/module/execute>` command is used to define what needs to be done to install this module in the image. It will be run at build time.
* A :doc:`run</descriptor/includes/run>` command sets the working directory and user that is used to launch the main process.


Tomcat
^^^^^^^^^
* Finally, create the following two files inside the ``tomcat`` directory:

.. code-block:: sh
   :caption: install.sh

   #!/bin/sh
   set -e
   tar -C /home/user -xf /tmp/artifacts/tomcat.tar.gz
   chown user:user -R /home/user

.. code-block:: yaml
   :caption: module.yaml

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

* The :doc:`artifact</descriptor/includes/artifacts>` command is used to retrieve external artifacts that need to be added to the image.



Move onto the :doc:`build section </getting-started/build>` to build this new image.
