
.. _repository_management:

Repository management
======================

One of the hardest challenges with we faced with Cekit is how to manage and define package repositories
correctly. Our current solution works in following scenarios:

1) Building CentOS based images
2) Building RHEL based images on subscribed hosts
3) Building RHEL based images on unsubscribed hosts


Best Practices
--------------

To achieve such behavior in Red Hat Middleware Container Images we created following rules and suggestions.

Defining repositories in container images
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

You should use :ref:`Plain<repo_plain>` repository definition for every repository as this will work easily on Red Hat subscribed host and will assume everyone one can rebuild are RHEL based images.


*Example:* Define Software Collections repository

.. code:: yaml

    packages:
        repositories:
            - name: SCL
              id: rhel-server-rhscl-7-rpms

If you have repository defined this way, Cekit will not try to enable it and will expect the repository to be forwarded from your host via Docker subscription plugin. When you want to build our image with CentOS base you need to override this repository.

*Example:* Override Software Collection repository for CentOS base

.. code:: yaml

    packages:
        repositories:
            - name: SCL
              rpm: centos-release-scl


.. note::
   See :ref:`Red Hat Repository<redhat_repo>` chapter which describes how Plain repositories are handled inside Red Hat Infrastructure.




