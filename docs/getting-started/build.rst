Building your image
====================

Now that a fully assembled image definition file has been constructed it is time to try building it. As mentioned previously we will use ``podman`` to build this image; for other build engines see :doc:`here </handbook/building/builder-engines>`

.. code-block:: sh

  $ cekit build podman

This will output various logs (extra detail is possible via the verbose ``-v`` option).

.. code-block:: none

   cekit -v build podman
   2019-04-05 13:23:37,408 cekit        INFO     You are running on known platform: Fedora 29 (Twenty Nine)
   2019-04-05 13:23:37,482 cekit        INFO     Generating files for podman engine
   2019-04-05 13:23:37,482 cekit        INFO     Initializing image descriptor...
   2019-04-05 13:23:37,498 cekit        INFO     Preparing resource 'modules'
   2019-04-05 13:23:37,510 cekit        INFO     Preparing resource 'example-common-module.git'
   ...
   STEP 41: FROM 850380a44a2b458cdadb0306fca831201c32d5c38ad1b8fb82968ab0637c40d0
   STEP 42: CMD ["/home/user/apache-tomcat-8.5.24/bin/catalina.sh", "run"]
   --> c55d3613c6a8d510c23fc56e2b56cf7a0eff58b97c262bef4f75675f1d0f9636
   STEP 43: COMMIT my-example:1.0
   2019-04-05 13:27:48,975 cekit        INFO     Image built and available under following tags: my-example:1.0, my-example:latest
   2019-04-05 13:27:48,977 cekit        INFO     Finished!

It is possible to use ``podman`` to list the new image e.g.

.. code-block:: sh

 $ podman images
 REPOSITORY                  TAG      IMAGE ID       CREATED          SIZE
 localhost/my-example        latest   c55d3613c6a8   48 seconds ago   709 MB
 localhost/my-example        1.0      c55d3613c6a8   48 seconds ago   709 MB
