..
   SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
   SPDX-License-Identifier: Apache-2.0

*************
Prerequisites
*************

The following packages are needed for |project| to work properly.

List of all needed dependencies:
================================

* python{{ py_req }}
{%- for dep in dependencies %}
* `{{ dep }}`
{%- endfor %}
