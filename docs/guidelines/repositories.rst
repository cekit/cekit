Repository guidelines
==========================


One of the biggest challenges we faced with CEKit is how to manage and define
package repositories correctly. This section focuses on best practices around
using package repositories.

CEKit support different ways of defining and injecting repositories. Besides this,
repositories can be manually managed by scripts in the modules itself.

Background
---------------

To give an overview on the available options, we need to understand the challenges too.
Among other things, two are the three visible ones:

#. Different requirements for repository access because of image types (community vs. product)
#. Image hierarchy
#. Source code requirement

Repositories availability
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

All public/community images have public repositories freely available. This applies to Fedora,
CentOS images, but as well to Ubuntu or Alpine. All images come with a set of repositories
already configured in the image itself and there is no need to do anything special to enable them.

On the other hand we have product images where repositories are guarded in some way,
for example by requiring subscriptions. Sometimes subscriptions are transparent
(need to be enabled on the host, but nothing needs to be done in the container),
sometimes we need to point to a specific location internally.

This makes it hard to have a single way to add or enable repositories.

Image hierarchy challenges
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Besides issues in repository management described above we can have issues
with how we structure images. For example the main image descriptor could be a community image,
using publicly available repositories. We could have an overrides file saved next to it
that would convert the image to be a product image, which obviously uses different sources
of packages.

Source code
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This is a bit related to the image hierarchy challenges above. If we build community images,
then we expect to have the source code in public. With product images this may or may not
be the same case.

In case where product images source is hosted internally only, we don't need to hide internal
package repositoties. But it we develop in the true open source spirit, everything should be
public. In such case, the product image descriptor cannot really refer to internal repositories
and we need to use available, public information and correctly point the builder to an internal
repository. This is very hard to do correctly.

Guidelines
-------------

This section describes best practices for managing repositories. We divided them into two
sub-sections: for community and product images.

Repositories in community images
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In case of community images, in most cases you will be fine with whatever is already
available in the image itself.

If you need to add some repository, we suggest to use one of three options:

1. Add a :ref:`package with repository definition <descriptor/image:RPM repository>`,
2. Add a :ref:`repository file definition <descriptor/image:URL repository>`,
3. Manage it manually (advanced).

RPM defined repositories
***********************************

First option is probably the cleanest one of all but it requires that a package with
the repository definition exists in the already enabled repositories. This is true for
example for `EPEL repository <https://fedoraproject.org/wiki/EPEL>`__
or `Software Collections repository <https://www.softwarecollections.org>`__.

.. code-block:: yaml

    packages:
        repositories:
            - name: scl
              rpm: centos-release-scl

Repository file defined repositories
*****************************************

Second option is to add prepared repository file.

.. code-block:: yaml

    packages:
        repositories:
            - name: foo
              url:
                repository: https://web.example/foo.repo

Here is an example repo file:

.. code-block:: ini

    [google-chrome]
    name=google-chrome
    baseurl=http://dl.google.com/linux/chrome/rpm/stable/x86_64
    enabled=1
    gpgcheck=1
    gpgkey=https://dl.google.com/linux/linux_signing_key.pub

It's easy to create one if need. Please note that it should be self-contained meaning that other
things must not be required to configure to make it work. A good practice is to save this file on
a host secured with SSL. The GPG key should be always provided, but in case of development repositories
it's OK to turn off GPG checking (set ``gpgcheck`` to ``0``).

Manual repository management
***********************************

Last option is all about manual repository management. This means that enabling and removing repositories
can be done as part of a module which directly creates repo files in the image while building it.

Enabling repositories this way needs to be well thought. Repositories will be available
for package installation in the **subsequent module execution**:

.. code-block:: yaml

    modules:
        install:
            - name: repository.enable
            - name: repository.packages.install

The reason for this is that
package installation is done **before** any commands are executed and since we enable the repository
as part of some command we cannot also request packages to be installed from that repository at that time.

There is one way to overcome this limitation.

Additionally to enabling the repository,
you can use the package manager to install packages you want. This gives you great flexibility.

Consider following module descriptor:

.. code-block:: yaml

    # SNIP
    execute:
        - script: packages.sh

and the ``packages.sh`` file content:

.. code-block:: bash

    #!/bin/bash

    curl -o /etc/yum.repos.d/foo.repo https://web.example/foo.repo
    dnf -y install foo-package

This combination allows you to fully control what is done to packages as part of the build process.

Repositories in product images
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. note::
    If your product image source code is not exposed to public as mentioned in the :ref:`previous section <guidelines/repositories:Source code>`, you may use
    the same :ref:`repository management methods as in community images <guidelines/repositories:Repositories in community images>`.

    Everything below covers the case where product image source code is public.

Managing repositories in product images is completely different from what we saw in community images.
The reason is that these require subscriptions to access them.

To enable repositories inside RHEL containers you need to subscribe the host. Read more about it
here: https://access.redhat.com/solutions/1443553.

Besides this, we can have following situations:

#. Building RHEL based images on subscribed hosts
#. Building RHEL based images on unsubscribed hosts

Plain repositories
**********************

:ref:`Plain repositories <descriptor/image:Plain repository>` are an abstract way of defining package repositories.
These are just markers that such and such repository is required to successfully build the image,
but because these do not reveal the *implementation* of the repository, CEKit is unable to
directly satisfy this requirement.

Why that would be a good thing? Because of two things:

#.  If you specify plain repository with a defined ``name`` -- it will be easy to override it!
    Additionally, the ``id`` key can suggest what should be the implementation of this repository definition, and
#.  For subscribed hosts, no repository preparation is required.

Let's take a look at an example.

.. code-block:: yaml

    packages:
        repositories:
            - name: scl
              id: rhel-server-rhscl-7-rpms

This could be later overridden with something like this:

.. code-block:: bash

    $ cekit build --overrides '{"packages": {"repositories": [{"name": "scl", "url": {"repository": "http://internal/scl.repo"}}]}}' podman

On a subscribed host, there would be no need to do above overrides, because automatically every repository attached
to a subscription is enabled in the container image running on that host.

.. warning::
    It is not possible to limit repositories available to a container running on a subscribed host outside of the container.
    You need to manage it in the container. See https://access.redhat.com/solutions/1443553 for detailed information about this.

Content sets
*****************

Using content sets is the **preferred way when building Red Hat container images**. Content sets define all the sources
for packages for particular container image.

A sample content sets file may look like this:

.. code-block:: yaml

    x86_64:
    - server-rpms
    - server-extras-rpms

    ppx64le:
    - server-for-power-le-rpms
    - server-extras-for-power-le-rpms

This defines architectures and appropriate repository ID's. Defining content sets can be done in the ``content_sets``
section. For details please take a look at the :ref:`image descriptor documentation <descriptor/image:Content sets>`.

Please note that the behavior of repositories when content sets are defined is different too;
**when content sets are used -- any repositories defined are ignored**. You will see a warning in the logs
if that will be the case. This means that if a repository is defined in any module
(see :ref:`note about this below <guidelines/repositories:Do not define repositories in modules>`)
or in image descriptor or in overrides -- it will be ignored.

.. note::
    If you want to enable content sets in OSBS, you need also set the ``pulp_repos`` key to ``true`` in the
    ``compose`` section of the :ref:`OSBS Configuration <descriptor/image:OSBS configuration>`.


Notes
-------------

Here are a few notes from our experience. Hopefully this will make repository management easier for you too!

Always define name of the repository
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

When you define the repository, you should always specify the ``name`` key. It should be
generic but self-explaining at the same time. This will make it much easier to understand
what repository it is and in case where it's not available, finding a replacement source
will be much easier task to do.

.. code-block:: yaml

    packages:
        repositories:
            - name: scl
              rpm: centos-release-scl

In this example, the ``scl`` is short and it clearly suggests Software Collections. Here is how it could be
redefined to use some internal repository.

.. code-block:: bash

    $ cekit build --overrides '{"packages": {"repositories": [{"name": "scl", "url": {"repository": "http://internal/scl.repo"}}]}}' podman

Do not define repositories in modules
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Although it is technically possible to define repositories in modules, it shouldn't be done. This makes is much harder
to manage and override it. In case you do not own the module that defines the repository,
you have little control over how it is defined and if it can be easily overridden.

Repositories should be a property of the image descriptor.

Use content sets for Red Hat images
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you are developing Red Hat container images, you should use content sets to define which repositories should be used.