Packages to reinstall
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Key
    ``reinstall``
Required
    No

Packages listed in the ``reinstall`` section are marked to be reinstalled in the container image.

.. code-block:: yaml

    packages:
        reinstall:
            - tzdata
