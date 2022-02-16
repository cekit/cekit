Package repositories
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Key
    ``repositories``
Required
    No

.. warning::
    Some package repositories are supported only on specific distributions and package manager
    combinations. Please refer to documentation below!

CEKit uses all repositories configured inside the image. You can also specify additional
repositories using repositories subsection.

.. tip::
    See :doc:`repository guidelines guide </guidelines/repositories>` to learn about best practices for repository
    definitions.

.. code-block:: yaml

    packages:
        repositories:
            - name: scl
              rpm: centos-release-scl
            - name: extras
              id: rhel7-extras-rpm
              description: "Repository containing extras RHEL7 extras packages"
