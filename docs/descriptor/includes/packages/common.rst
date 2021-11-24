Packages
----------

Key
    ``packages``
Required
    No


To install additional packages you can use the ``packages``
section where you specify package names and repositories to be used, as well
as the package manager that is used to manage packages in this image.

.. code-block:: yaml
    :caption: Example package section for RPM-based distro

    packages:
        repositories:
            - name: extras
                id: rhel7-extras-rpm
        manager: dnf
        manager_flags:
        install:
            - mongodb24-mongo-java-driver
            - postgresql-jdbc
            - mysql-connector-java
            - maven
            - hostname

.. code-block:: yaml
    :caption: Example package section for Alpine Linux

    packages:
        manager: apk
        install:
            - python3

.. code-block:: yaml
    :caption: Example package section for APT-based distro

    packages:
        manager: apt-get
        install:
            - python3-minimal
