Content sets
**************************

.. note::
    Available only on RPM-based distributions.

Content sets are tightly integrated to OSBS style of defining repositories in ``content_sets.yml`` file.
If this kind of repository is present in the image descriptor it overrides all other repositories types.
For local Docker based build these repositories are ignored similarly to Plain repository types and
we expect repository definitions to be available inside image. See
`upstream docs <https://osbs.readthedocs.io/en/latest/users.html#content-sets>`_ for more details about
content sets.

.. note::
   Behavior of Content sets repositories is changed when running in :doc:`Red Hat Environment </handbook/redhat>`.

.. warning::
   Content sets can be defined only on the image level!

There are two possibilities how to define Content sets type of repository:

Embedded content sets
++++++++++++++++++++++++

In this approach content sets are embedded inside image descriptor under the ``content_sets`` key.

.. code-block:: yaml

    packages:
        content_sets:
            x86_64:
            - server-rpms
            - server-extras-rpms


Linked content sets
++++++++++++++++++++++++

In this approach Contet sets file is linked from a separate yaml file next to image descriptor via
``content_sets_file`` key.

Image descriptor:

.. code-block:: yaml

    packages:
        content_sets_file: content_sets.yml


``content_sets.yml`` located next to image descriptor:

.. code-block:: yaml

     x86_64:
       - server-rpms
       - server-extras-rpms
