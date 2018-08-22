
.. _repository_management:

Repository management
======================

One of the hardest challenges we faced with Cekit is how to manage and define package repositories
correctly. Our current solution works in following scenarios:

1) Building CentOS or Fedora based images
2) Building RHEL based images on subscribed hosts
3) Building RHEL based images on unsubscribed hosts


Best Practices
--------------

To achieve such behavior in Red Hat Middleware Container Images we created following rules and suggestions.

Defining repositories in container images
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

You should use :ref:`Plain<repo_plain>` repository definition for every repository as this will work easily on Red Hat subscribed host and will assume everyone can rebuild are RHEL based images.


*Example:* Define Software Collections repository

.. code:: yaml

    packages:
        repositories:
            - name: SCL
              id: rhel-server-rhscl-7-rpms

If you have repository defined this way, Cekit will not try to inject it and will expect the repository to be already available inside your container image. If it's not provided by the image (for example repository definition already available in ``/etc/yum.repos.d/`` directory) or the host (for example on via `subscribed RHEL host <https://access.redhat.com/solutions/1443553>`_) you need to override this repository. To override a repository definition you need to specify a repository with same ``name``. By overriding Plain repository type, you are actually saying that you have an external mechanism to inject the repository inside the image. This can be any supported :ref:`repository type<repo>`.

.. note::
   You can view Plain repository type as an abstract classes and ODCS, RPM and URL repositories as an actual implementation.

*Example:* Override Software Collection repository for CentOS base

.. code:: yaml

    packages:
        repositories:
            - name: SCL
              rpm: centos-release-scl

*Example:* Override Software Collections repository with a custom yum repository file

.. code:: yaml

    packages:
        repositories:
            - name: SCL
              url:
	        repository: https://foo.lan/scl.repo
		gpg: https://foo.lan/scl.gpg

*Example:* Override Software Collections repository with an ODCS

.. code:: yaml

    packages:
        repositories:
            - name: SCL
              odcs:
	        pulp: rhel-server-rhscl-7-rpms


.. note::
   See :ref:`Red Hat Repository<redhat_repo>` chapter which describes how Plain repositories are handled inside Red Hat Infrastructure.




