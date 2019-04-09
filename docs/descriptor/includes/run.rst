Run
---

Key
    ``run``
Required
    No

The ``run`` section encapsulates instructions related to launching main process
in the container including: ``cmd``, ``entrypoint``, ``user`` and ``workdir``.
All subsections are described later in this paragraph.

Below you can find full example that uses every possible option.

.. code-block:: yaml

    run:
        cmd:
            - "argument1"
            - "argument2"
        entrypoint:
            - "/opt/eap/bin/wrapper.sh"
        user: "alice"
        workdir: "/home/jboss"


Cmd
^^^

Key
    ``cmd``
Required
    No

Command that should be executed by the container at run time.

.. code-block:: yaml

    run:
        cmd:
            - "some cmd"
            - "argument"

Entrypoint
^^^^^^^^^^

Key
    ``entrypoint``
Required
    No

Entrypoint that should be executed by the container at run time.

.. code-block:: yaml

    run:
        entrypoint:
            - "/opt/eap/bin/wrapper.sh"

User
^^^^^^^^^^^^^^^^^^^^

Key
    ``user``
Required
    No

Specifies the user (can be username or uid) that should be used to launch the main
process.

.. code-block:: yaml

    run:
        user: "alice"

Working directory
^^^^^^^^^^^^^^^^^^^^

Key
    ``workdir``
Required
    No


Sets the current working directory of the entrypoint process in the container.

.. code-block:: yaml

    run:
        workdir: "/home/jboss"
