.. _image_help_pages:

Image Help Pages
================

At image build-time, CEKit generates a "help" documentation page, which is
saved adjacent to the generate image sources. The help page can optionally be
included into the image. The template used to generate the help page can be
overridden by the user's configuration file, or the input image configuration,
either via the central image.yaml file, included modules or overrides.

Adding the help page to your image
----------------------------------

There are two ways to instruct CEKit to add the help page to your image: either
Specify ``--add-help`` on the command-line when running the *build* phase, or
via your configuration file, in the *doc* section:

.. code::

  [doc]
  addhelp = true

Providing your own help page template
-------------------------------------

The default help template is supplied within CEKit. You can override it for
every image via your configuration, or on a per-image basis in the image
definition.

Via configuration
^^^^^^^^^^^^^^^^^

**Example**:

.. code::

   [doc]
   help_template = /home/jon/something/my_help.md

Via image definition
^^^^^^^^^^^^^^^^^^^^

This could be in the master ``image.yaml``, or in a module referenced from the
``image.yaml``, or on the command-line via ``--overrides`` or
``--overrides-file``:

**Example**:

.. code::

   …
   help:
     template: /home/jon/something/my_help.md

