Packages to remove
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Key
    ``remove``
Required
    No

Packages listed in the ``remove`` section are marked to be removed from the container image.

.. code-block:: yaml

    packages:
        remove:
            - postgresql-jdbc
