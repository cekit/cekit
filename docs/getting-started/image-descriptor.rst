Preparing image descriptor
============================

This section will guide you through a very simple example.

1. Using a standard text editor create an empty ``image.yml`` file. It is recommended to use the ``image.yaml`` naming scheme.
2. As described in :doc:`Image Descriptor </descriptor/index>` several values are mandatory. Add the following to the file:

.. code-block:: yaml

   name: my-example
   version: 1.0
   from: centos:7

* Next, while optional, it is recommended to add a suitable ``description`` tag e.g.

.. code-block:: yaml

    description: My Example Tomcat Image

While this configuration will build in CEKit it isn't very interesting as it will simply create another image layered on top of CentOS 7.

It is possible to directly add further content to the image at this point through a variety of methods. ``packages`` (see  :doc:`here </descriptor/includes/packages>`) can be used to add further RPMs ; for example:

.. code-block:: yaml

   packages:
      install:
        - postgresql-jdbc


Now if this image is built (``cekit build podman``) then it is possible to access the image and see that ``postgresql-jdbc`` is now installed e.g.

.. code-block:: sh

   podman run -it --rm $(podman images -q | head -1) /bin/bash
   [root@f845a92c2370 /]# rpm -q postgresql-jdbc
   postgresql-jdbc-9.2.1002-6.el7_5.noarch

However in general modules are used as the 'building blocks' to assemble the image - they can be used as individual libraries or shared blocks across multiple images. So, move onto to :doc:`modules </getting-started/modules>` to discover more about these.
