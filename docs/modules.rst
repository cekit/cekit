.. _modules:

Modules
=======

Modules are the **most important** concept in Concreate.

It is very important to make a module self-containg which means that executing
scripts defined in the module's definition file should always end up in a state
where you could define the module as being `installed`.

Modules can be stacked -- some modules will be run before, some after you module.
Please keep that in mind that at the time when you are developing a module -- you don't
know how and when it'll be executed.

Module descriptor
-----------------

Module and image descriptor share the same schema. Please refer to the :ref:`image descriptor documentation <image_descriptor>`
for more information.

Module descriptor extends image descriptor by adding the ``execute`` section
(described below) and by making the ``version`` key optional.

``execute``
^^^^^^^^^^^

Execute section defines what needs to be done to install this module in the image.
Every execution listed in this section will be run at image build time in the order
as defined.

.. code:: yaml

    execute:
          # The install.sh file will be executed first as root user
        - execute: install.sh
          # Then the redefine.sh file will be executed as jboss user
        - execute: redefine.sh
          user: jboss

.. note::

    When no ``user`` is defined, ``root`` user will be used to execute the script.

Best practices
--------------

Storing modules
^^^^^^^^^^^^^^^

We can find two most common use cases for storing modules:

1. Together with the image descriptor,
2. In external repository.

What fits the best for you depends on your project. If you are going to create a self-contained
image then most probably you should be fine with local modules

In case you are developing image that requires a module potentially being usefull for other images
-- you should develop that module independently of the image itself. External modules are all about
reusing code across various images. In fact this was the initial idea for the whole project --
make it easy to share code between images.

Local modules
^^^^^^^^^^^^^

To make it easy to develop images quickly we added support for local modules,
where the module source is stored together with the image descriptor.

By convention -- if you place your modules to the ``modules`` directory next to image
descriptor -- all modules will be **automatically discovered** without the need to define them in
image descriptor, which is the same asdefining it this way:

.. code:: yaml

    modules:
      repositories:
        - path: modules

Script parametrization
^^^^^^^^^^^^^^^^^^^^^^^^

To parametrize your scripts you can use environment variables. Module installation
should not require any parameters.
