~~~~~~~~~
CHANGELOG
~~~~~~~~~
1.6.0
=====
Release date:
  2013-11-20
Notes:
  * Adds support for Django's multi-database features.
  * Updates readme

v1.4.3
======
Release date:
  2012-01-04
Notes:
  * Adds signals around state transition executions (``before_state_execute``
    and ``after_state_execute`` in ``states2.signals``)
  * Updates docs

v1.4.2
======
Release date:
  2011-11-05
Notes:
  * Updates ``StateGroup`` to support an exclude list (instead of stating all
    states that included in the group, state the ones that are not included)
  * Updates ``get_admin_actions`` to support a non-default (``state``) field
    name
  * Updates docs

v1.4.1
======
Release date:
  2011-10-28
Notes:
  * Store the version differently in Sphinx configuration

v1.4.0
======
Release date:
  2011-10-28
Notes:
  * Adds documentation
  * Adds supports for ``StateGroup``
  * Supports multiple ``from_states`` in ``StateTransition``
  * Adds ``graph_states``

v1.3.11
=======
Release date:
  2011-09-22
Notes:
  * Updates ``save()`` to support disabling state validation (used mainly
    during migrations)
  * Reverts change of v1.3.10 in ``get_STATE_info``

v1.3.10
=======
Release date:
  2011-08-31
Notes:
  * Corrects ``get_STATE_info``

v1.3.9
======
Release date:
  2011-08-17
Notes:
  **same as v1.3.7**

v1.3.8
======
Release date:
  2011-08-24
Notes:
  **broken release** -- replaced by v1.3.9 in the meantime

v1.3.7
======
Release date:
  2011-08-17
Notes:
  * Hide the ``KeyError`` that could be raised by ``get_state``
  * Corrects the ``__init__`` calls in the exceptions

v1.3.6
======
Release date:
  2011-08-16
Notes:
  * Moves the ``ValidationError`` to the ``states2.exceptions``

v1.3.5
======
Release date:
  2011-08-12
Notes:
  * Adds transition validation

v1.3.4
======
Release date:
  2011-08-10
Notes:
  * Removes forgotten ``pdb`` statement

v1.3.3
======
Release date:
  2011-08-10
Notes:
  * Corrects overridden ``save()``: use the ``class_prepared`` signal to
    rewrite the ``save()``

v1.3.2
======
Release date:
  2011-07-18
Notes:
  * Corrects overridden ``save()``: handler only needs to be called when object
    is created

v1.3.1
======
Release date:
  2011-07-18
Notes:
  * Corrects overridden ``save()`` (first save the DB, then call the handler)

v1.3.0
======
Release date:
  2011-07-08
Notes:
  * Adds an handler that will be called after the object arrived in a new
    state
  * Overriding the ``save()`` method of models from now on

v1.2.21
=======
Release date:
  2011-07-18
Notes:
  **incorrect tag** -- replaced by 1.3.1

v1.2.20
=======
Release date:
  2011-05-13
Notes:
  * Print the traceback when an exception occurs during a failed state
    transition

v1.2.19
=======
Release date:
  2011-05-06
Notes:
  * Use custom exception instead of a plain ``Exception``

v1.2.18
=======
Release date:
  2011-05-02
Notes:
  * Use the ``get_state_info()`` method instead of deep-calling the
    ``StateMachine``

v1.2.17
=======
Release date:
  2011-05-02
Notes:
  * Updates South support
  * Store transition kwargs in log

v1.2.16
=======
Release date:
  2011-04-29
Notes:
  * Created a ``StateField`` (and updated ``StateModel`` to use this)
  * Removed model cache. Use the one build into Django.

v1.2.15
=======
Release date:
  2011-04-28
Notes:
  * Added Gert to authors
  * Moved code outside the src dir into a top-level dir
  * Added version information to the module
  * Created a machine module
  * Added generic base exception
  * Updated the README file

    * Cleaned up documentation
    * Converted to ReST syntax
  * PEP8-ify

Older versions
==============
- v1.2.14
- v1.2.13
- v1.2.12
- v1.2.11
- v1.2.10
- v1.2.9
- v1.2.8
- v1.2.7
- v1.2.6
- v1.2.5
- v1.2.4
- v1.2.3
- v1.2.2
- v1.2.1
- v1.1.1
