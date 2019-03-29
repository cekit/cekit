Volumes
-------

Key
    ``volumes``
Required
    No

In case you want to define volumes for your image, just use the ``volumes`` section!

.. code-block:: yaml

    volumes:
        - name: "volume.eap"
          path: "/opt/eap/standalone"

.. note::

    The ``name`` key is optional. If not specified the value of ``path`` key will be used.

