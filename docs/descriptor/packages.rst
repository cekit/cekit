``packages``
------------

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

``repositories``
----------------
Cekit uses all repositories configured inside the image. You can also specify additional
repositories using repositories subsection. Cekit currently supports three ways of defining
additional repositories:

* RPM
* ODCS
* URL

``RPM``
^^^^^^^^
This ways is using repository configuration files and related keys packaged as an RPM.

**Example**: To enable `CentOS SCL <https://wiki.centos.org/AdditionalResources/Repositories/SCL>`_ inside the
image you should define repository in a following way:

.. code:: yaml

    packages:
        repositories:
            - name: scl
	      rpm: centos-release-scl


``ODCS``
^^^^^^^^^
This way is instructs `ODCS <https://pagure.io/odcs>`_ to generate on demand pulp repositories.
To use ODCS define repository section in following way:

.. code:: yaml

    packages:
        repositories:
            - name: foo
	      odcs:
	        pulp: rhel-7-extras-rpm
		
.. note::

   Only on demand pulp ODCS repositories are supported now.


``URL``
^^^^^^^^
This approach enables you to download a yum repository file and corresponding GPG key. To do it, define
repositories section in a way of:

.. code:: yaml

    packages:
        repositories:
            - name: foo
	      url:
	        repository: https://web.example/foo.repo
                gpg: https://web.exmaple/foo.gpg
