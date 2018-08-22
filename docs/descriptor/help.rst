
help
----

The optional help sub-section defines a single key ``template``, which can be used
to define a filename to use for generating image documentation at build time. By
default, a template supplied within Cekit is used.

At image build-time, the template is interpreted by the `Jinja2
<http://jinja.pocoo.org/>`_ template engine.  For a concrete example, see the
`default help.jinja supplied in the Cekit source code
<https://github.com/cekit/cekit/blob/develop/cekit/templates/help.jinja>`_.

.. code:: yaml

  help:
    template: myhelp.jinja
