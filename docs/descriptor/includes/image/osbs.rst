OSBS
------

Key
    ``osbs``
Required
    No

This section represents object we use to hint OSBS builder with a configuration which needs to be tweaked
for successful and reproducible builds.

It contains two main keys:

* :ref:`repository <descriptor/image:OSBS repository>`
* :ref:`configuration <descriptor/image:OSBS configuration>`


.. code-block:: yaml

    osbs:
        repository:
            name: containers/redhat-openjdk-18
            branch: jb-openjdk-1.8-openshift-rhel-7
        configuration:
            container:
                compose:
                    pulp_repos: true

OSBS extra directory
^^^^^^^^^^^^^^^^^^^^^

Key
    ``extra_dir``
Required
    No

If a directory name specified by ``extra_dir`` key will be found next to the image descriptor, this directory **and** its contents will be copied into the target directory and later to the dist-git directory.

Symbolic links are preserved (not followed).

Copying is done before generation, which means that files from the extra directory can be overridden
in the :ref:`generation phase<handbook/building/build-process:Generating required files>` .

.. note::
    If you do not specify this key in image descriptor, the default value of ``osbs_extra`` will be used.

.. code-block:: yaml

    osbs:
        extra_dir: custom-files

OSBS extra copy command
^^^^^^^^^^^^^^^^^^^^^^^^

Key
    ``extra_dir_target``
Required
    No

This optional key is used in conjunction with ``extra_dir`` above. If this key is specified, then the ``extra_dir``
will be placed within the container image at the location denoted by ``extra_dir_target``. If this is *not* set,
no ``COPY`` commands will be added.

For example, with the value of ``/`` then the contents from dist-git will be copied to the
root of the image filesystem

.. code-block:: bash
    :caption: Dist-git source control

    osbs-extra/
        foobar.yaml
        manifests/
            ...
        metadata/
            ...

.. code-block:: yaml
    :caption: CEKit Yaml file

    osbs:
        extra_dir: osbs-extra
        extra_dir_target: /

.. code-block:: bash
    :caption: Container image file system

    /
        foobar.yaml
        manifests/
            ...
        metadata/
            ...

With the below example both a different source directory in dist-git and a different target directory within the
container image is used.

.. code-block:: bash
    :caption: Dist-git source control

    custom-files/
        a-directory/
            ...

.. code-block:: yaml
    :caption: CEKit Yaml file

    osbs:
        extra_dir: custom-files
        extra_dir_target: /image-user/tmp

.. code-block:: bash
    :caption: Container image file system

    /
        image-user/
            tmp/
                a-directory/
                    ...


OSBS repository
^^^^^^^^^^^^^^^^

Key
    ``repository``
Required
    No

This key serves as a hint which DistGit repository and its branch we use to push generated sources into.

.. code-block:: yaml

    osbs:
        repository:
            name: containers/redhat-openjdk-18
            branch: jb-openjdk-1.8-openshift-rhel-7

OSBS Koji target
^^^^^^^^^^^^^^^^^^^^^

Key
    ``koji_target``
Required
    No

To execute a build in OSBS the Koji target parameter needs to be provided. By default it is
constructed based on the branch name (see above), like this:

.. code-block::

    [BRANCH_NAME]-containers-candidate

In most cases this is what is expected, but sometimes you want to change this. An example of such
situation is when you use a custom, private branch to execute a scratch build. Target can be
overridden by specifying the ``koji_target`` key.

.. code-block:: yaml

    osbs:
        koji_target: rhaos-middleware-rhel-7-containers-candidate

OSBS configuration
^^^^^^^^^^^^^^^^^^^

Key
    ``configuration``
Required
    No

This key is holding OSBS ``container.yaml`` file. See `OSBS docs <https://osbs.readthedocs.io/en/latest/users.html?highlight=container.yaml#image-configuration>`__
for more information about this file.

CEKit supports two ways of defining content of the  ``container.yaml`` file:

1. It can be embedded in ``container`` key, or
2. It can be injected from a file specified in ``container_file`` key.

Selecting preferred way of defining this configuration is up to the user.
Maintaining external file may be handy in case where it is shared across
multiple images in the same repository.


Embedding
    In this case whole ``container.yaml`` file is embedded in an image descriptor
    under the ``container`` key.

    .. code-block:: yaml

        # Embedding
        osbs:
            configuration:
                # Configuration is embedded directly in the container key below
                container:
                    compose:
                        pulp_repos: true
Linking
    In this case ``container.yaml`` file is read from a file located next to the image descriptor
    using the ``container_file`` key to point to the file.

    .. code-block:: yaml

        osbs:
            configuration:
                # Configuration is available in the container.yaml file
                container_file: container.yaml


    and ``container.yaml`` file content:

    .. code-block:: yaml

        compose:
            pulp_repos: true

OSBS Gating Files
^^^^^^^^^^^^^^^^^

The ``gating.yaml`` file is used within the Container Verification Pipeline (CVP). Both live within the dist-git repository
next to the Dockerfile. The configuration within CEKit is very similar to :ref:`OSBS configuration <descriptor/image:OSBS configuration>`

Due to the CVP definition including custom tags embedded definitions are not supported ; instead the ``gating_file``
key should be used to specify the file to include.

For example:

    .. code-block:: yaml

        osbs:
            configuration:
                gating_file: gating.yaml
                container:
                    ...