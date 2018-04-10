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

``common``
------------

``work_dir``
^^^^^^^^^^^^

Contains location of Cekit working directory, which is used to store some persistent data like
dist_git repositories.

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

:: _repo_inject:

 Repository injection
^^^^^^^^^^^^^^^^^^^
There are multiple possibilities how to inject repository inside the image and its configurable in the ``~/.cekit/config``. The configuration follows this scheme:

.. code::

   [repositories-$builder]
   $repo_name = $action

Where:

* ``$builder`` - one of supported builder (docker, osbs)

* ``$repo_name`` - name of the repository

* ``$action`` - one of the following actions:

  1) **odcs-pulp** - default for OSBS builder

     Aks odcs to create a temporary repository from an existing pulp repository. Repository name is taken from
     ``repository`` atribute of the repository section.

  2) **rpm**

     Install repository from rpm via yum. Mostly used for epel/scl in Centos. RPM name is taken from ``repository``
     attribute of the repository section.

  3) **dummy** - default for Docker builder

     Threats the repository as only documentation note, that this repo should be available in the image. It
     does not inject/enable it in the image.

*Example*: To define that Software collection repository will be installed via RPM for Docker builder and injected via ODCS pulp for OSBS you need to put following lines into you ``~/.cekit/config`` file:

.. code::

   [repositories-docker]
   scl = rpm

   [repositories-osbs]
   scl = odcs-pulp
