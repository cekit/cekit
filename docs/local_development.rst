Developing modules locally
==========================

Cekit enables you to use a work in progress modules to build the image by exploiting its overrides system. As an example, imagine we have very simple image which is using one module from a cct_module repository like this:

.. code:: yaml

  schema_version: 1
  name: "dummy/example"
  version: "0.1"
  from: "jboss/openjdk18-rhel7:1.1"
  modules:
    repositories:
      - git:
        url: https://github.com/jboss-openshift/cct_module.git
        ref: master
    install:
      - name: s2i-common


Now imagine,  we have found a bug in its s2i-common module. We will clone the module repository localy by executing:

1. Clone cct_module to your workstation to ``~/repo/cct_module``

.. code:: bash

  $ git clone https://github.com/jboss-openshift/cct_module.git /home/user/repo/cct_module

2. Then we will create override.yaml next to the image.yaml, override.yaml should look like:

.. code:: yaml

  schema_version: 1
  modules:
    repositories:
      - path: "/home/user/repo/cct_module"

3. We now can build the image using overridden module by executing:

.. code:: bash

  $ cekit generate --overrides overrides.yaml

4. When your work is finished, commit and push your changes to a module repository and remove overrides.yaml

Injecting local artifacts
=========================

During module/image development there can be a need to use locally built artifact instead of a released one. The easiest way to inject
such artifact is to use override mechanism.


To override an artifact imagine, that you have an artifact defined in a way:

.. code:: yaml

	  - md5: d31c6b1525e6d2d24062ef26a9f639a8
	    name: jolokia.jar
	    url: https://maven.repository.redhat.com/ga/org/jolokia/jolokia-jvm/1.5.0.redhat-1/jolokia-jvm-1.5.0.redhat-1-agent.jar

And you want to inject a local build of new version of our artifact. To archive it you need to create following override:

.. code:: yaml

	  - md5: ~
	    name: jolokia.jar
	    path: /tmp/build/jolokia.jar

Note ``~`` for ``md5`` key. Its very important as it removes value of this key. This will result in an artifact without any checksum defined and Cekit will replace its every time. See :ref:`Removing keys<remove_keys>` for more details.


.. note::
   If the artifacts lacks the name key, its automatically created by using basename of the artifact path or url.
