..
   SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
   SPDX-License-Identifier: Apache-2.0

*************************
Documentation development
*************************

The following command deletes previous built documentation and derives
docs out of code:

.. code:: bash

    make -C docs apidoc

The following command builds the docs:

.. code:: bash

    make -C docs html

The resulting documentation build should be available in `docs/build/html`,
entry point is `index.html`
