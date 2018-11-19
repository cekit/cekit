OSBS
----
This section represents object we use to hint OSBS builder with a configuration which needs to be tweaked
for successful and reproducible builds.

It contains two main keys:

* ``repository``
* ``configuration``

Repository
^^^^^^^^^^
This key serves as a hint which DistGit repository and its branch we use to push generated sources into.


**Example:**

.. code:: yaml

    osbs:
        repository:
              name: containers/redhat-openjdk-18
              branch: jb-openjdk-1.8-openshift-rhel-7



Configuration
^^^^^^^^^^^^^
This key is holding OSBS ``container.yaml`` file ( :ref:`docs<https://osbs.readthedocs.io/en/latest/users.html?highlight=container.yaml#image-configuration>`_ )
``container.yaml`` file can be embedded in ``container`` key or inject from a file specified in ``container_file`` key.


Embedded
""""""""
In this case whole ``container.yaml`` file is embedded in an image descriptor.

.. code:: yaml

    osbs:
        configuration:
           container:
              compose:
                  pulp: True

Linked
""""""

In this case ``container.yaml`` file is save next to the image descriptor.

.. code:: yaml

    osbs:
        configuration:
            container_file: container.yaml


and ``container.yaml`` file contains:

.. code:: yaml

    compose:
        pulp: True
