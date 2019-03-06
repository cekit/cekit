
.. _redhat_env:

Red Hat Environment
===================
If you are running CEKit in Red Hat internal infrastructure it behaves differently. This behavior is triggered by changing :ref:`redhat configuration option<redhat_config>` in CEKit configuration file.


Tools
-----
CEKit integration with following tools is changed in following ways:

* runs ``rhpkg`` instead of ``fedpkg``
* runs ``odcs`` command with ``--redhat`` option set


Environment Variables
---------------------

Following variables are added into the image:

* ``JBOSS_IMAGE_NAME`` - contains name of the image
* ``JBOSS_IMAGE_VERSION`` - contains version of the image

Labels
------

Following labels are added into the image:

* ``name`` - contains name of the image
* ``version`` - contains version of the image

.. _redhat_repo:

Repositories
------------

In Red Hat we are using ODCS/OSBS integration to access repositories for building our container images. To make our life easier
for local development CEKit is able to ask ODCS to create ``content_sets.yml`` based repositories even for local Docker builds.
This means that if you set :ref:`redhat configuration option<redhat_config>` to True, your content_sets repositories will be
injected into the image you are building and you can successfully build an image on non-subscribed hosts.

Artifacts
---------

In Red Hat environment we are using Brew to build our packages and artifacts. CEKit provides an integration layer with Brew and enables to use artifact directly from Brew. To enable this set :ref:`redhat configuration option<redhat_config>` to True and define artifact **only** by specifying its ``md5`` checksum.


*Example:* Following artifact will be fetched directly from brew for Docker build and uses `Brew/OSBS inegration <https://osbs.readthedocs.io/en/latest/users.html#fetch-artifacts-url-yaml>`_ for OSBS build.

.. code:: yaml

    artifacts:
      - md5: d31c6b1525e6d2d24062ef26a9f639a8
        name: jolokia-jvm-1.5.0.redhat-1-agent.jar

