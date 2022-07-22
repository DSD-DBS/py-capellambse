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
