Help
------

Key
    ``help``
Required
    No

The ``help.md`` file functions as a container's man page - see
`here <https://github.com/projectatomic/container-best-practices/blob/master/creating/help.adoc>`__ for more information.
At image build-time CEKit can generate a documentation page about the image. This file is a
human-readable conversion of the resulting image descriptor. That is,
a descriptor with all overrides and modules combined together, which was used
to build the image.

If an image help page is requested to be added to the image (by setting the ``add`` key),
a ``help.md`` is generated and added to the **dist-git** repository.

**By default image help pages are not generated**.

The default help template is supplied within CEKit. You can override it for
every image via image definition. The optional help sub-section defines
a key ``template``, which can be used to define a filename to use for generating
image documentation at build time.

The filename may be absolute or a relative path. If the latter it is used as relative to the image descriptor.
For modules a relative path will be relative to the module root.

.. code-block:: sh

   cat test_module/module.yaml
   version: '1.0'
   name: test_module
   help:
     add: true
     template: help.jinja

Note that if the ``template`` denotes a file *without* any substitution markers then effectively the file is copied
to the dist-git repository as ``help.md`` verbatim.

.. code-block:: yaml

   help:
     add: true
     template: my_help.md

The template is interpreted by the `Jinja2
<http://jinja.pocoo.org/>`__ template engine. For a simple example with a image descriptor containing:

.. code-block:: yaml

    schema_version: 1
    name: test/image
    version: 2
    from: centos:7
    ...

and a help file (which may be named ``help.jinja``, ``help.md`` etc) containing:

.. code-block:: md

    % {{ name }}

    # NAME

    Operator - My operator metadata for version {{ version }}

    # USAGE

    This container image can be used only as part of my operator.

will produce the following rendered Markdown file:

.. code-block:: md

    % test/image

    # NAME

    Operator - My operator metadata for version 2

    # USAGE

    This container image can be used only as part of my operator.

For a more detailed template example, see the
`default help.jinja supplied in the CEKit source code
<https://github.com/cekit/cekit/blob/develop/cekit/templates/help.jinja>`__.

.. warning::
    If multiple help templates are used (e.g. in modules), as they cannot be merged the last one will be used.