
.. _redhat_env:

Red Hat Environment
===================
If you running Cekit in Red Hat internal infrastructure it behaves differently. This behavior is triggered by changing :ref:`redhat configuration option<redhat_config>` in Cekit configuration file.


Tools
-----
Cekit integration with following tools is changed in following ways:

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
* ``architecture`` - contains architecture of the image

.. _redhat_repo:

Repositories
------------

As we are building on not properly subscribed RHEL system and using internal repositories we need
to convert our plain type repositories into OSBS ones.

*Example:* Following :ref:`Plain<repo_plain>` repository:

.. code:: yaml

    packages:
        repositories:
            - name: SCL
              id: rhel-server-rhscl-7-rpms

will be automatically converted into following :ref:`ODCS<repo_odcs>` repository:

.. code:: yaml

    packages:
        repositories:
            - name: SCL
              odcs:
                  pulp: rhel-server-rhscl-7-rpms
