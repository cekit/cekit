Overrides
=========

During an image life cycle there can be a need to do a slightly tweaked builds - using different base images, injecting newer libraries etc. We want to support such scenarios without a need of duplicating whole image sources. To achieve this Cekit supports overrides mechanism for its image descriptor. You can override almost anything in image descriptor. The overrides are based on overrides descriptor - a YAML object containing overrides for the image descriptor.

To use an override descriptor you need to pass ``--overides-file`` argument to a Cekit. You can also pass  YAML object representing changes directly via ``--overrides`` option.

**Example**: To use overrides.yaml file located in current working directory run:

.. code:: bash

	  $ cekit build --overrides-file overrides.yaml


**Example**: To override a label via command line run:

.. code:: bash

	  $ cekit build --overrides "{'labels': [{'name': 'foo', 'value': 'overriden'}]}"



How overrides works
-------------------

Cekit is using `YAML <http://yaml.org/>`_ format for its descriptors. Overrides in cekit works on `YAML node <http://www.yaml.org/spec/1.2/spec.html#id2764044>`_ level.


Scalar nodes
^^^^^^^^^^^^
Scalar nodes are easy to override, if Cekit finds any scalar node in an overrides descriptor it updates its value in image descriptor with the overridden one.

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
Sequence nodes are little bit tricky, if they're representing plain arrays, we cannot easily override any value so Cekit is just merging arrays from image and override descriptors together.

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
	    - "echo"
	    - "foo"

**Known issues**: Merging sequence nodes can have surprising results, please see `corresponding issue. <https://github.com/jboss-container-images/cekit/issues/106>`_

Mapping nodes
^^^^^^^^^^^^^
Mappings are merged via *name* key. If Cekit is overriding an mapping or array of mappings it tries to find a **name** key in mapping and use and identification of mapping. If two **name** keys matches, all keys of the mapping are updated.

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
