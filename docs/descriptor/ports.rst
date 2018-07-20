Ports
-----

This section is used to mark which ports should be exposed in the
container. If we want to highlight a port used in the container, but not necessary expose
it -- we should set the ``expose`` flag to ``false`` (``true`` by default).

.. code:: yaml

    ports:
        - value: 8443
        - value: 8778
          expose: false
