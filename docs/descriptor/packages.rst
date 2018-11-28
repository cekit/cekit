Packages
--------

To install additional RPM packages you can use the ``packages``
section where you specify package names and repositories to be used.

.. code:: yaml

    packages:
        install:
            - mongodb24-mongo-java-driver
            - postgresql-jdbc
            - mysql-connector-java
            - maven
            - hostname

Packages are defined in the ``install`` subsection.

.. _repo:

Repositories
------------
Cekit uses all repositories configured inside the image. You can also specify additional
repositories using repositories subsection. Cekit currently supports following multiple ways of defining
additional repositories:

* Plain
* RPM
* URL
* ContentSets

.. note::
   See :ref:`Repository mangement<repository_management>` to learn about best practices for repository
   definitions.

.. _repo_plain:

Plain
^^^^^
This is the default option. With this approach you specify repository id and Cekit will not perform any action and expect the repository definition exists inside the image. This is useful as a hint which repository must be present for particular image to be buildable. The definition can be overridden by your preferred way of injecting repositories inside the image.

.. code:: yaml

    packages:
        repositories:
            - name: extras
              id: rhel7-extras-rpm
              description: "Repository containing extras RHEL7 extras packages"


RPM
^^^^
This ways is using repository configuration files and related keys packaged as an RPM.

**Example**: To enable `CentOS SCL <https://wiki.centos.org/AdditionalResources/Repositories/SCL>`_ inside the
image you should define repository in a following way:

.. code:: yaml

    packages:
        repositories:
            - name: scl
              rpm: centos-release-scl

.. _repo_odcs:


URL
^^^^
This approach enables you to download a yum repository file and corresponding GPG key. To do it, define
repositories section in a way of:

.. code:: yaml

    packages:
        repositories:
            - name: foo
              url:
                repository: https://web.example/foo.repo
                gpg: https://web.exmaple/foo.gpg


.. _repo_contentsets:


Content sets
^^^^^^^^^^^^
Content sets are tightly integrated to OSBS style of defining repositories in ``content_sets.yml`` file.
If this kind of repository is present in the image descriptor it overrides all other repositories types.
For local Docker based build these repositories are ignored similarly to Plain repository types and
we expect repository definitions to be available inside image. See
`upstream docs <https://osbs.readthedocs.io/en/latest/users.html#content-sets>`_ for more details about
content sets.

.. note::
   Behavior of Content sets repositories is changed when running in :ref:`Red Hat Environment<redhat_env>`.

There are two possibilities how to define Content sets type of repository:

Embedded
""""""""
In this approach content sets are embedded inside image descriptor under the ``content_sets`` key.

.. code:: yaml

    packages:
        content_sets:
            x86_64:
            - server-rpms
            - server-extras-rpms


Linked
""""""
In this approach Contet sets file is linked from a separate yaml file next to image descriptor via
``content_sets_file`` key.

Image descriptor:

.. code:: yaml

    packages:
        content_sets_file: content_sets.yml


``content_sets.yml`` located next to image descriptor:

.. code:: yaml

     x86_64:
       - server-rpms
       - server-extras-rpms
