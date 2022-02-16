RPM repository
*******************

.. note::
    Available only on RPM-based distributions.

This way is using repository configuration files and related keys packaged as an RPM.

**Example**: To enable `CentOS SCL <https://wiki.centos.org/AdditionalResources/Repositories/SCL>`_ inside the
image you should define repository in a following way:

.. code-block:: yaml

    packages:
        repositories:
            - name: scl
              rpm: centos-release-scl

.. tip::
    The ``rpm`` key can also specify a URL to a RPM file:

    .. code-block:: yaml

        packages:
            repositories:
                - name: epel
                  rpm: https://dl.fedoraproject.org/pub/epel/epel-release-latest-7.noarch.rpm

.. warning::
    Images with `microdnf` do not not support installing from a remote URL. To work around this, the current recommended option is
    to use a module and use ``rpm -i`` to enable the new repo.
