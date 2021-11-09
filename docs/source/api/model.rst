The Model
=========

``MelodyModel`` is the entry point to the capellambse functionality.
A Capella (``aird``) model can be loaded by instantiating a model,
providing it the right path.

The model follows the structure used in Capella/ARCADIA:

* ``oa``: Operational Architecture
* ``sa``: System Analysis
* ``la``: Logical Architecture
* ``pa``: Physical Architecture

From the layers it's possible to discover the components and functions.

::

   >>> from capellambse import MelodyModel
   >>> model = MelodyModel("capella-python-api/capella-python-api.aird")
   >>> model.la.all_components
   <CoupledElementList at 0x00007F4E771DA680 [<LogicalComponent 'Logical System' (6f6bd619-72ab-4983-970f-07fda0fa10fd)>]>
   >>> model.la.all_functions
   <CoupledElementList at 0x00007F4E74CF6CE0 [<LogicalFunction 'Root Logical Function' (f18b6427-24d7-4c29-a4a5-abb0ebde3ec2)>, ...]>
   >>> model.oa.all_classes
   <CoupledElementList at 0x00007F4E771DA680 [<Class 'LogicalFunction' (89aa96d2-3cec-49cb-ad63-db14506ea764)>, ...]>

Elements can be modified and the model can be saved.

.. autoclass:: capellambse.model.MelodyModel
   :members:
   :undoc-members:
   :show-inheritance:
