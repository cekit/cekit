Configuration file
==================

Concreate can be configured using a configuration file. We use the
properties file format.

Concreate will look for this file at the path ``~/.concreate``.

Below you can find description of available sections together with options described in detail.

``[common]``
------------

``ssl_verify``
^^^^^^^^^^^^^^

Controls verification of SSL certificates for example when downloading artifacts. Default: ``True``.

.. code::

    [common]
    ssl_verify = False

``cache_url``
^^^^^^^^^^^^^

Specifies a different location that could be used to fetch artifacts. Usually this is a URL to some cache service.
By default it is not set.

You can use following substitutions:

* ``#filename#`` -- the file name from the url of the artifact
* ``#algorithm#`` -- has algorithm specified for the selected artifact
* ``#hash#`` -- value of the digest.

**Example**

Consider you have an image definition with artifacts section like this:

.. code:: yaml

    artifacts:
        - url: "http://some.host.com/7.0.0/jboss-eap-7.0.0.zip"
          md5: cd02482daa0398bf5500e1628d28179a

If we set the ``cache_url`` parameter in following way:

.. code::

    [common]
    cache_url = http://cache.host.com/fetch?#algorithm#=#hash#

The JBoss EAP artifact will be fetched from: ``http://cache.host.com/fetch?md5=cd02482daa0398bf5500e1628d28179a``.

And if we do it like this:

.. code::

    [common]
    cache_url = http://cache.host.com/cache/#filename#

The JBoss EAP artifact will be fetched from: ``http://cache.host.com/cache/jboss-eap-7.0.0.zip``.

.. note::

    In all cases digest will be computed from the downloaded file and compared with the expected value.

``[repository]``
----------------

``urls``
^^^^^^^^

The ``urls`` setting in the ``repository`` section can be used to define YUM/DNF repository files
that should be added to the image at build time.

In case you have YUM/DNF repo files that you want to put to the ``/etc/yum.repos.d`` directory to enable additional
repositories Concreate can handle it for you automatically.

Concreate will copy all repo files defined in the ``urls`` parameter to ``/etc/yum.repos.d`` directory and
enable them to be used while installing packages listed in the packages section.

At the end of the image build process Concreate removes newly added repo files from the ``/etc/yum.repos.d``
directory automatically. If you do not want to have these files removed after installation --
you need to make your repo files part of some module that installs them in the correct place.

There are a few rules about repositories added that way:

1. This feature covers only the situation where you want to add a custom repo file at build time but you do not want it to be enabled in containers.
2. Repo file name should be the same as the repo id in the repository (the name between square brackets).
3. There should be only one repository per file.
4. Only added repositories will be enabled during install of packages, all other repositories (including default) will be disabled.

Example

.. code::

    [repository]
    urls = http://host.com/some.repo,http://otherhost/other.repo
