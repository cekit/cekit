Overrides
=========

During an image life cycle there can be a need to do a slightly tweaked builds - using different base images, injecting newer libraries etc. We want to support such scenarios without a need of duplicating whole image sources. To achieve this Concreate supports overrides mechanism for its image descriptor. You can override almost anything in image descriptor. The overrides are based on overrides descriptor - a yaml file containing changes to image descriptor.

To use an override descriptor you need to pass ``--overides <PATH>`` argument to a concreate.

**Example**: To use overrides.yaml  file located in current working directory run:

.. code:: bash

	  $ concreate build --overrides=overrides.yaml

How overrides works
-------------------

Concreate is using `YAML <http://yaml.org/>`_ format for its descriptors. Overrides in concreate works on `YAML node <http://www.yaml.org/spec/1.2/spec.html#id2764044>`_ level.


Scalar nodes
^^^^^^^^^^^^
Scalar nodes are easy to overrides, if Concreate finds any scalar node in a overrides descriptor it update its value in image descriptor with the overridden one.

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
Sequence nodes are little bit tricky, if they're representing plain arrays, we cannot easily override any value so Concreate is just merging arrays from image and override descriptors together. This can have unexpected results, please see `corresponding issue. <https://github.com/jboss-container-images/concreate/issues/106>`_

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

Mapping nodes
^^^^^^^^^^^^^
Mappings are merged via *name* key. If Concreate is overriding an mapping or array of mappings it tries to find a *name* key in mapping and use and identification of mapping. If two *name* keys matches, all keys of the mapping are updated.

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
