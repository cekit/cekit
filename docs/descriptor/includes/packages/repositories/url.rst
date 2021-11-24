URL repository
*******************

.. note::
    Available only on RPM-based distributions.

This approach enables you to download a yum repository file. To do it, define
repositories section in a way of:

.. code-block:: yaml

    packages:
        repositories:
            - name: foo
              url:
                repository: https://web.example/foo.repo
