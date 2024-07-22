..
   SPDX-FileCopyrightText: Copyright DB InfraGO AG
   SPDX-License-Identifier: Apache-2.0

*************************
Documentation development
*************************

First, make sure that the necessary dependencies for building documentation are
installed:

.. code:: bash

   pip install '.[docs]'

The following command builds the documentation:

.. code:: bash

   make -C docs html

The resulting documentation build will be available in ``docs/build/html``.

Instead, you can also use ``make -C docs serve`` to (re-)build the docs and start a
local server, which can be accessed on http://localhost:8000.

The following command deletes previously built documentation:

.. code:: bash

   make -C docs clean
