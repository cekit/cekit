Packages
----------

Key
    ``packages``
Required
    No


To install additional RPM packages you can use the ``packages``
section where you specify package names and repositories to be used, as well
as the package manager that is used to manage packages in this image.

.. code-block:: yaml

    packages:
        repositories:
            - name: extras
                id: rhel7-extras-rpm
        manager: dnf
        install:
            - mongodb24-mongo-java-driver
            - postgresql-jdbc
            - mysql-connector-java
            - maven
            - hostname

Packages to install
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Key
    ``install``
Required
    No

Packages listed in the ``install`` section are marked to be installed in the container image.

.. code-block:: yaml

    packages:
        install:
            - mongodb24-mongo-java-driver
            - postgresql-jdbc

Package manager
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Key
    ``manager``
Required
    No

It is possible to define package manager used in the image
used to install packages as part of the build process.

Currently available options are ``yum``, ``dnf``, and ``microdnf``.

.. note::
    If you do not specify this key the default value is ``yum``.
    
    It will work fine on Fedora and RHEL images because OS maintains
    a symlink to the proper package manager. 

.. code-block:: yaml

    packages:
        manager: dnf
        install:
            - git

Package repositories
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Key
    ``repositories``
Required
    No

CEKit uses all repositories configured inside the image. You can also specify additional
repositories using repositories subsection. CEKit currently supports following ways of defining
additional repositories:

* `Plain repository <#plain-repository>`__
* `RPM repository <#rpm-repository>`__
* `URL repository <#url-repository>`__
* `Content sets <#content-sets>`__

.. tip::
    See :doc:`repository guidelines guide </guidelines/repositories>` to learn about best practices for repository
    definitions.

.. code-block:: yaml

    packages:
        repositories:
            - name: scl
              rpm: centos-release-scl
            - name: extras
              id: rhel7-extras-rpm
              description: "Repository containing extras RHEL7 extras packages"


Plain repository
*******************

With this approach you specify repository ``id`` and CEKit will not perform any action
and expect the repository definition exists inside the image. This is useful as a hint which
repository must be present for particular image to be buildable. The definition can be overridden
by your preferred way of injecting repositories inside the image.

.. code-block:: yaml

    packages:
        repositories:
            - name: extras
              id: rhel7-extras-rpm
              description: "Repository containing extras RHEL7 extras packages"

RPM repository
*******************

This ways is using repository configuration files and related keys packaged as an RPM.

**Example**: To enable `CentOS SCL <https://wiki.centos.org/AdditionalResources/Repositories/SCL>`_ inside the
image you should define repository in a following way:

.. code-block:: yaml

    packages:
        repositories:
            - name: scl
              rpm: centos-release-scl

.. tip::
    The ``rpm`` key can also specify a URL to a RPM file:

    .. code-block:: yaml

        packages:
            repositories:
                - name: epel
                  rpm: https://dl.fedoraproject.org/pub/epel/epel-release-latest-7.noarch.rpm

URL repository
*******************

This approach enables you to download a yum repository file and corresponding GPG key. To do it, define
repositories section in a way of:

.. code-block:: yaml

    packages:
        repositories:
            - name: foo
              url:
                repository: https://web.example/foo.repo

Content sets
**************************


Content sets are tightly integrated to OSBS style of defining repositories in ``content_sets.yml`` file.
If this kind of repository is present in the image descriptor it overrides all other repositories types.
For local Docker based build these repositories are ignored similarly to Plain repository types and
we expect repository definitions to be available inside image. See
`upstream docs <https://osbs.readthedocs.io/en/latest/users.html#content-sets>`_ for more details about
content sets.

.. note::
   Behavior of Content sets repositories is changed when running in :doc:`Red Hat Environment </handbook/redhat>`.

There are two possibilities how to define Content sets type of repository:

Embedded content sets
++++++++++++++++++++++++

In this approach content sets are embedded inside image descriptor under the ``content_sets`` key.

.. code-block:: yaml

    packages:
        content_sets:
            x86_64:
            - server-rpms
            - server-extras-rpms


Linked content sets
++++++++++++++++++++++++

In this approach Contet sets file is linked from a separate yaml file next to image descriptor via
``content_sets_file`` key.

Image descriptor:

.. code-block:: yaml

    packages:
        content_sets_file: content_sets.yml


``content_sets.yml`` located next to image descriptor:

.. code-block:: yaml

     x86_64:
       - server-rpms
       - server-extras-rpms
