Args
------

Key
    ``args``
Required
    No

Every image can include arg instructions. See https://docs.docker.com/engine/reference/builder/#arg for more
details. CEKit makes it easy to do so with the ``args`` section. An optional default value may be provided.

.. note::

    ARGS will be rendered before any environment variables, labels or execution sections.

.. code-block:: yaml

    args:
        - name: "user1"
          value: "someuser"
        - name: "QUARKUS_EXTENSION"
        - name: "ARG_WITH_DESCRIPTION"
          example: "ARG_WITH_DESCRIPTION=a-value"
          description: "Example argument."
