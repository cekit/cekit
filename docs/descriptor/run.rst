``run``
-------

The ``run`` section encapsulates instructions related to launching main process
in the container including: ``cmd``, ``entrypoint``, ``user`` and ``workdir``.
All subsections are described later in this paragraph.

Below you can find full example that uses every possible option.

.. code:: yaml

    run:
        cmd:
            - "argument1"
            - "argument2"
        entrypoint:
            - "/opt/eap/bin/wrapper.sh"
        user: "alice"
        workdir: "/home/jboss"


``cmd``
^^^^^^^

Command that should be executed by the container at run time.

.. code:: yaml

    run:
        cmd:
            - "some cmd"
            - "argument"

``entrypoint``
^^^^^^^^^^^^^^

Entrypoint that should be executed by the container at run time.

.. code:: yaml

    run:
        entrypoint:
            - "/opt/eap/bin/wrapper.sh"
