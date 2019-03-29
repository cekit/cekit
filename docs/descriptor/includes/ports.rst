Ports
-----

Key
    ``ports``
Required
    No

This section is used to mark which ports should be exposed in the
container. If we want to highlight a port used in the container, but not necessary expose
it -- we should set the ``expose`` flag to ``false`` (``true`` by default).

You can provide additional documentation as to the usage of the port with the
keys ``protocol``, to specify which IP protocol is used over the port number (e.g
TCP, UDP…) and ``service`` to describe what network service is running on top
of the port (e.g. "http", "https"). You can provide a human-readable long form
description of the port with the ``description`` key.

.. code-block:: yaml

    ports:
        - value: 8443
          service: https
        - value: 8778
          expose: false
          protocol: tcp
          description: internal port for communication.
