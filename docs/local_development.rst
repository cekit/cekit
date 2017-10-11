Developing modules locally
==========================

Concreate was designed in a way, that it always tries to build image by fetching latest released modules available. This makes it a very good fit into any ci/automated environment but it can create a hard workflows for module developers. We can address this issue by using overrides mechanism which is integral part of the Concreate.

Imagine we have very simple image which is using one module from a cct_module repository like this:

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


And we are in a need of updating s2i-common module. To achieve this one of the possible way is to:

1. Clone cct_module to your workstation to ``~/repo/cct_module``

.. code:: bash

  $ git clone https://github.com/jboss-openshift/cct_module.git /home/user/repo/cct_module

2. Create override.yaml next to the image.yaml. override.yaml should look like:

.. code:: yaml

  modules:
    repositories:
      - path: "/home/user/repo/cct_module"

3. Build image using overrided module by executing:

.. code:: bash

  $ concreate generate --overrides overrides.yaml

4. When your work is finished, commit and push your changes to a module repository and remove overrides.yaml
