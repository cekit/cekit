# Minimal makefile for Sphinx documentation
#

# You can set these variables from the command line.
SPHINXOPTS    =
SPHINXBUILD   = python -msphinx
SPHINXPROJ    = CEKit
SOURCEDIR     = .
BUILDDIR      = _build

# Handle either python2/3 RPM and PIP based install of sphinx-autobuild
SPHINXAUTOBUILD := $(shell command -v sphinx-autobuild || command -v sphinx-autobuild-3 2> /dev/null)

# Put it first so that "make" without argument is like "make help".
help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

preview: clean
	@$(SPHINXAUTOBUILD) -b html $(SOURCEDIR) $(BUILDDIR)/html

.PHONY: help Makefile

# Catch-all target: route all unknown targets to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINXOPTS).
%: Makefile
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
