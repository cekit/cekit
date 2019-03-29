Help
------

Key
    ``help``
Required
    No

At image build-time CEKit can generate a documentation page about the image. This file is a
human-readable conversion of the resulting image descriptor. That is,
a descriptor with all overrides and modules combined together, which was used
to build the image.

If an image help page is requested to be added to the image (by setting the ``add`` key),
a ``help.md`` is generated and added to the **root of the image**.

**By default image help pages are not generated**.

The default help template is supplied within CEKit. You can override it for
every image via image definition. The optional help sub-section can define defines
a single key ``template``, which can be used
to define a filename to use for generating image documentation at build time.

The template is interpreted by the `Jinja2
<http://jinja.pocoo.org/>`__ template engine.  For a concrete example, see the
`default help.jinja supplied in the CEKit source code
<https://github.com/cekit/cekit/blob/develop/cekit/templates/help.jinja>`__.

.. code-block:: yaml

   help:
     add: true
     template: my_help.md
