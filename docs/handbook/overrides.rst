Overrides
=========

During an image life cycle there can be a need to do a slightly tweaked builds - using different base images, injecting newer libraries etc. We want to support such scenarios without a need of duplicating whole image sources. To achieve this CEKit supports overrides mechanism for its image descriptor. You can override almost anything in image descriptor. The overrides are based on overrides descriptor - a YAML object containing overrides for the image descriptor.

To use an override descriptor you need to pass ``--overrides-file`` argument to a CEKit. You can also pass JSON/YAML object representing changes directly via ``--overrides`` command line argument.

**Example**: To use overrides.yaml file located in current working directory run:

.. code:: bash

	  $ cekit build --overrides-file overrides.yaml


**Example**: To override a label via command line run:

.. code:: bash

	  $ cekit build --overrides "{'labels': [{'name': 'foo', 'value': 'overridden'}]}"

Overrides Chaining
------------------

You can even specify multiple overrides. Overrides are resolved that last specified is the most important one. This means that values from *last override specified overrides all values from former ones*.

**Example**: If you run following command, label `foo` will be set to `baz`.

.. code:: bash

	  $ cekit build --overrides "{'labels': [{'name': 'foo', 'value': 'bar'}]} --overrides "{'labels': [{'name': 'foo', 'value': 'baz'}]}"

How overrides works
-------------------

CEKit is using `YAML <http://yaml.org/>`_ format for its descriptors. Overrides in cekit works on `YAML node <http://www.yaml.org/spec/1.2/spec.html#id2764044>`_ level.


Scalar nodes
^^^^^^^^^^^^
Scalar nodes are easy to override, if CEKit finds any scalar node in an overrides descriptor it updates its value in image descriptor with the overridden one.

**Example**: Overriding scalar node:

*image descriptor*

.. code:: yaml

	  schema_version: 1
	  name: "dummy/example"
	  version: "0.1"
	  from: "busybox:latest"

*overrides descriptor*

.. code:: yaml

	  schema_version: 1
	  from: "fedora:latest"

*overridden image descriptor*

.. code:: yaml

	  schema_version: 1
	  name: "dummy/example"
	  version: "0.1"
	  from: "fedora:latest"

Sequence nodes
^^^^^^^^^^^^^^
Sequence nodes are little bit tricky, if they're representing plain arrays, we cannot easily override any value so CEKit is just replacing the whole sequence.

**Example**: Overriding plain array node:

*image descriptor*

.. code:: yaml

	  schema_version: 1
	  name: "dummy/example"
	  version: "0.1"
	  from: "busybox:latest"
	  run:
	    cmd:
	    - "echo"
	    - "foo"

*overrides descriptor*

.. code:: yaml

	  schema_version: 1
	  run:
	    cmd:
	    - "bar"

*overridden image descriptor*

.. code:: yaml

	  schema_version: 1
	  name: "dummy/example"
	  version: "0.1"
	  from: "busybox:latest"
	  run:
	    cmd:
  	    - "bar"


Mapping nodes
^^^^^^^^^^^^^
Mappings are merged via *name* key. If CEKit is overriding an mapping or array of mappings it tries to find a **name** key in mapping and use and identification of mapping. If two **name** keys matches, all keys of the mapping are updated.

**Example**: Updating mapping node:

*image descriptor*

.. code:: yaml

	  schema_version: 1
	  name: "dummy/example"
	  version: "0.1"
	  from: "busybox:latest"
	  envs:
	  - name: "FOO"
	    value: "BAR"

*overrides descriptor*

.. code:: yaml

	  schema_version: 1
	  envs:
	  - name: "FOO"
	    value: "new value"

*overridden image descriptor*

.. code:: yaml

	  schema_version: 1
	  name: "dummy/example"
	  version: "0.1"
	  from: "busybox:latest"
	  envs:
	  - name: "FOO"
	    value: "new value"


Removing keys
---------------

Overriding can result into a need of removing any key from a descriptor. You can achieve this by overriding a key with a YAML null value ``~``.

**Example**: Remove value from a defined variable

If you have a variable defined in a following way:

.. code:: yaml

	  envs:
	    - name: foo
	      value: bar

you can remove ``value`` key via following override:

.. code:: yaml

	  envs:
	    - name: foo
	      value: ~

It will result into following variable definition:


.. code:: yaml

	  envs:
	    - name: foo



