Is it running?
====================

Now lets try running the image. As was shown in the preceeding example it is possible to obtain the image id through the ``podman images`` command. To ensure the local host machine can see the image the following command will map port 8080 to 32597.

.. code-block:: sh

 $ podman run -p 32597:8080 localhost/my-example:1.0

When the image is built it is automatically tagged using the ``name`` key in the image descriptor combined with the ``version`` key. As the tomcat module that was specified earlier included a :doc:`run </descriptor/include/run>` command it will automatically start the Tomcat webserver.

Using your browser go to http://localhost:32597 ; if successful then the image is running correctly.

Note: if you want to interactively explore the new image use the following command:

.. code-block:: sh

 $ podman run -it --rm localhost/my-example:1.0 /bin/bash

.. note::
   It is also possible to reference using the image id e.g. ``podman run -it --rm $(podman images -q | head -1) /bin/bash``.

Once an interactive shell has been started on the image it is possible to verify the JDK has been installed e.g.

.. code-block:: sh

   $ podman run -it --rm my-example:latest /bin/bash
   [user@ff7b60ea4d7c ~]$ rpm -qa | grep openjdk-devel
   java-1.8.0-openjdk-devel-1.8.0.201.b09-2.el7_6.x86_64
