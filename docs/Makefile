# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: CC0-1.0

# Minimal makefile for Sphinx documentation
#

# You can set these variables from the command line, and also
# from the environment for the first two.
SPHINXOPTS    ?= -W
SPHINXBUILD   ?= sphinx-build
SOURCEDIR     = source
BUILDDIR      = build

# Put it first so that "make" without argument is like "make help".
help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

.PHONY: help Makefile

# Catch-all target: route all unknown targets to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINXOPTS).
%: Makefile
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)


# Auto-generate API documentation
apidoc:
	sphinx-apidoc --module-first --output-dir source/code --force .. \
		../capellambse/aird/diagram.py \
		../capellambse/extensions/reqif/elements.py \
		../capellambse/repl.py \
		../capellambse/sphinx.py
	sed -i -e '/^\.\. automodule:: capellambse$$/a \   :no-index:' source/code/capellambse.rst

clean-apidoc:
	rm -rfv source/code

.PHONY: apidoc clean-apidoc
clean: clean-apidoc

.PHONY: serve
html: apidoc
serve: html
	cd build/html && exec python -m http.server --bind 127.0.0.1
