Configuration file
==================

Cekit can be configured using a configuration file. We use the
properties file format.

Cekit will look for this file at the path ``~/.cekit/config``. Its location can be changed via command line ``--config`` option.

**Example**
Running Cekit with different config file:

.. code:: sh
	  
	  $ cekit --config ~/alternative_path build

Below you can find description of available sections together with options described in detail.

.. contents::


``common``
------------

.. _workdir_config:

``work_dir``
^^^^^^^^^^^^

Contains location of Cekit working directory, which is used to store some persistent data like
dist_git repositories.

.. code:: yaml

    [common]
    work_dir=/tmp


``ssl_verify``
^^^^^^^^^^^^^^

Controls verification of SSL certificates for example when downloading artifacts. Default: ``True``.

.. code:: yaml

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

.. _redhat_config:

``redhat``
^^^^^^^^^^
This option changes Cekit default options to comply with Red Hat internal infrastructure and policies.



**Example**: To enable this flag add following lines into your ``~/.cekit/config`` file:

.. code::

   [common]
   redhat = true

.. note::

   If you are using Cekit within Red Hat infrastructure you should have valid Kerberos ticket.
