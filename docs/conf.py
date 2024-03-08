# -*- coding: utf-8 -*-

import os
import sys

sys.path.insert(0, os.path.abspath(".."))
sys.path.append(os.path.abspath("./_ext"))

from cekit.version import __version__ as cekit_version  # noqa: E402

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinx.ext.graphviz",
    "sphinx.ext.autosectionlabel",
    "sphinx.ext.todo",
    "schema",
    "sphinx_copybutton",
]
# http://www.sphinx-doc.org/en/master/usage/extensions/autosectionlabel.html#confval-autosectionlabel_prefix_document
autosectionlabel_prefix_document = True
autosectionlabel_maxdepth = 4

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

source_suffix = ".rst"

# The toctree document.
master_doc = "index"

# General information about the project.
project = "CEKit"
copyright = "2017-2024, CEKit Team"
author = "CEKit Team"

# The short X.Y version.
version = ".".join(cekit_version.split(".")[0:2])
# The full version, including alpha/beta/rc tags.
release = cekit_version

language = "en"

exclude_patterns = ["_build", ".venv", "venv"]

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = "monokai"

# If true, `todo` and `todoList` produce output, else they produce nothing.
todo_include_todos = True

html_show_sourcelink = False
html_static_path = ["_static"]
htmlhelp_basename = "cekitdoc"
html_theme = "furo"

html_theme_options = {
    "globaltoc_collapse": True,
    "top_of_page_button": None,
}

html_sidebars = {
    "**": [
        "sidebar/scroll-start.html",
        "logo.html",
        "sidebar/search.html",
        "sidebar/navigation.html",
        "sidebar/ethical-ads.html",
        "sidebar/scroll-end.html",
    ]
}
