Execute
---------

Key
    ``execute``
Required
    No

Execute section defines what needs to be done to install this module in the image.
Every execution listed in this section will be run at image build time in the order
as defined.

.. note::

    When no ``user`` is defined, ``root`` user will be used to execute the script.

.. code-block:: yaml

    execute:
        # The install.sh file will be executed first as root user
        - script: install.sh
        # Then the redefine.sh file will be executed as jboss user
        - script: redefine.sh
          user: jboss