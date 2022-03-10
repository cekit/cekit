# -*- coding: utf-8 -*-

import os
import sys

import guzzle_sphinx_theme

sys.path.insert(0, os.path.abspath('..'))
sys.path.append(os.path.abspath("./_ext"))

from cekit.version import __version__ as cekit_version


def setup(app):
    app.add_stylesheet('css/custom.css')


# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = ['sphinx.ext.graphviz', 'sphinx.ext.autosectionlabel', 'sphinx.ext.todo', 'schema']
# http://www.sphinx-doc.org/en/master/usage/extensions/autosectionlabel.html#confval-autosectionlabel_prefix_document
autosectionlabel_prefix_document = True
autosectionlabel_maxdepth = 4

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

source_suffix = '.rst'

# The toctree document.
master_doc = 'index'

# General information about the project.
project = u'CEKit'
copyright = u'2017-2019, CEKit Team'
author = u'CEKit Team'

# The short X.Y version.
version = '.'.join(cekit_version.split('.')[0:2])
# The full version, including alpha/beta/rc tags.
release = cekit_version

language = None

exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store', 'venv']

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# If true, `todo` and `todoList` produce output, else they produce nothing.
todo_include_todos = True

html_show_sourcelink = False
html_static_path = ['_static']

htmlhelp_basename = 'cekitdoc'

html_translator_class = 'guzzle_sphinx_theme.HTMLTranslator'
html_theme_path = guzzle_sphinx_theme.html_theme_path()
html_theme = 'guzzle_sphinx_theme'

extensions.append("guzzle_sphinx_theme")

html_theme_options = {
    "globaltoc_collapse": True,
    "project_nav_name": "CEKit",
    "globaltoc_depth": 4,
    "google_analytics_account": "UA-134837956-2"
}


html_sidebars = {
    '**': [
        'logo.html',
        'globaltoc.html',
        'searchbox.html'
    ]
}
