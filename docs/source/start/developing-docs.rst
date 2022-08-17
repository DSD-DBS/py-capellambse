..
   SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
   SPDX-License-Identifier: Apache-2.0

*************************
Documentation development
*************************

The following command derives docs out of code:

.. code:: bash

    sphinx-apidoc --output-dir docs/source/code --force .

The following command builds the docs:

.. code:: bash

    make -C docs html

The resulting documentation build should be available in `docs/build/html`, entry point is `index.html`
