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
