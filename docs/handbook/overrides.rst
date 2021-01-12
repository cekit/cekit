Overrides
=========

.. contents::
    :backlinks: none

During an image life cycle there can be a need to do a slightly tweaked builds --
using different base images, injecting newer libraries etc. We want to support such
scenarios without a need of duplicating whole image sources.

To achieve this CEKit **supports overrides mechanism** for its descriptors. You can override
anything from the descriptor. The overrides are based on overrides descriptor --
a YAML object containing overrides for the image descriptor.

To use an override descriptor you need to pass ``--overrides-file`` argument to
CEKit. You can also pass JSON/YAML object representing changes directly via
``--overrides`` command line argument.

Example
    Use ``overrides.yaml`` file located in current working directory

    .. code-block:: bash

        $ cekit build --overrides-file overrides.yaml podman


Example
    Override a label via command line

    .. code-block:: bash

        $ cekit build --overrides '{"labels": [{"name": "foo", "value": "overridden"}]}' podman

Overrides chaining
------------------

You can even specify multiple overrides. Overrides are resolved that last specified
is the most important one. This means that values from **last override specified overrides all values from former ones**.

Example
    If you run following command, label ``foo`` will be set to ``baz``.

    .. code-block:: bash

	    $ cekit build --overrides "{'labels': [{'name': 'foo', 'value': 'bar'}]} --overrides "{'labels': [{'name': 'foo', 'value': 'baz'}]}" podman

How overrides works
-------------------

CEKit is using `YAML <http://yaml.org/>`__ format for its descriptors.
Overrides in CEKit works on `YAML node <http://www.yaml.org/spec/1.2/spec.html#id2764044>`__ level.


Scalar nodes
^^^^^^^^^^^^
Scalar nodes are easy to override, if CEKit finds any scalar node in an overrides
descriptor it updates its value in image descriptor with the overridden one.

Example
    Overriding scalar node

    .. code-block:: yaml

        # Image descriptor

        schema_version: 1
        name: "dummy/example"
        version: "0.1"
        from: "busybox:latest"

    .. code-block:: yaml

        # Override descriptor

        schema_version: 1
        from: "fedora:latest"

    .. code-block:: yaml

        # Resulting image descriptor

        schema_version: 1
        name: "dummy/example"
        version: "0.1"
        from: "fedora:latest"

Sequence nodes
^^^^^^^^^^^^^^
Sequence nodes are a little bit tricky, if they're representing plain arrays,
we cannot easily override any value so CEKit is just replacing the whole sequence.

Example
    Overriding plain array node.

    .. code-block:: yaml

        # Image descriptor

        schema_version: 1
        name: "dummy/example"
        version: "0.1"
        from: "busybox:latest"
        run:
            cmd:
                - "echo"
                - "foo"

    .. code-block:: yaml

        # Override descriptor

        schema_version: 1
        run:
            cmd:
                - "bar"

    .. code-block:: yaml

        # Resulting image descriptor

        schema_version: 1
        name: "dummy/example"
        version: "0.1"
        from: "busybox:latest"
        run:
            cmd:
                - "bar"

Mapping nodes
^^^^^^^^^^^^^

Mappings are merged via ``name`` key. If CEKit is overriding a mapping or array of mappings
it tries to find a ``name`` key in mapping and use and identification of mapping.
If two ``name`` keys matches, all keys of the mapping are updated.

Example
    Updating mapping node.

    .. code-block:: yaml

        # Image descriptor

        schema_version: 1
        name: "dummy/example"
        version: "0.1"
        from: "busybox:latest"
        envs:
            - name: "FOO"
              value: "BAR"

    .. code-block:: yaml

        # Override descriptor

        schema_version: 1
        envs:
            - name: "FOO"
              value: "new value"

    .. code-block:: yaml

        # Resulting image descriptor

        schema_version: 1
        name: "dummy/example"
        version: "0.1"
        from: "busybox:latest"
        envs:
            - name: "FOO"
              value: "new value"


Removing keys
---------------

Overriding can result into need of removing a key from a descriptor.
You can achieve this by overriding a key with a `YAML null value <https://yaml.org/type/null.html>`__.

You can use either the ``null`` word or the tilde character: ``~`` to remove particular
key.

Example
    Remove value from a defined variable.

    If you have a variable defined in a following way:

    .. code-block:: yaml

        envs:
            - name: foo
              value: bar

    you can remove ``value`` key via following override:

    .. code-block:: yaml

        envs:
            - name: foo
              value: ~

    It will result into following variable definition:

    .. code-block:: yaml

        envs:
            - name: foo

.. warning::
    In some cases it will not be possible to remove the element and an error saying that
    schema cannot be validated will be shown. If you run it again with verbose output enabled
    (``--verbose``) you will see ``required.novalue`` messages.

    Improvement to this behavior is tracked here: https://github.com/cekit/cekit/issues/460

Artifact Overrides
------------------

While artifact overrides function in general as per  :ref:`scalar nodes <handbook/overrides:Scalar Nodes>` there is some
special case handling.

If the original definition contains a non-default destination e.g. ``/destination`` and the override does **not** specify
a destination then the original value will be maintained rather than overwriting it with the default value of
``/tmp/artifacts``.


Examples
^^^^^^^^

1. Maintain destination with plain override with new target

    .. code-block:: py
       :caption: Original (URL artifact)

        name: 'original-bar.jar'
        dest: '/tmp/destination/'
        url: 'https://foo/original-bar.jar'
        target: 'original-bar.jar'

    .. code-block:: yaml
       :caption: Overrides (Plain artifact)

        name: 'bar.jar'
        md5: 234234234234
        target: 'bar2222.jar'

    .. code-block:: yaml
       :caption: Result

        name: 'bar.jar'
        dest: '/tmp/destination/'
        md5: 234234234234
        target: 'bar2222.jar'


2. Maintain destination with plain override with generated target:

    .. code-block:: py
       :caption: Original (URL artifact)

        name: 'original-bar.jar'
        dest: '/tmp/destination/'
        url: 'https://foo/original-bar.jar'
        target: 'original-bar.jar'

    .. code-block:: yaml
       :caption: Overrides (Plain artifact)

        name: 'bar.jar'
        md5: 234234234234

    .. code-block:: yaml
       :caption: Result

        name: 'bar.jar'
        dest: '/tmp/destination/'
        md5: 234234234234
        target: 'bar.jar'
