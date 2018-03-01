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
