##################
Django States (v2)
##################

Authors:

- Jonathan Slenders, City Live nv
- Gert van Gool, City Live nv
- Maarten Timmerman, City Live nv

Description
-----------
State engine for django models. Define a state graph for a model and
remember the state of each object.  State transitions can be logged for
objects.


Usage example
-------------
It's basically these two things:

- Derived your model from ``StateModel``
- Add a ``Machine`` class to your model, for the state machine

::

    from states2.models import StateMachine, StateDefinition, StateTransition
    from states2.models import StateModel

    class PurchaseStateMachine(StateMachine):
       log_transitions = True

       # possible states
       class initiated(StateDefinition):
           description = _('Purchase initiated')
           initial = True

       class paid(StateDefinition):
           description = _('Purchase paid')

           def handler(self, instance):
               code_to_execute_when_arriving_in_this_state()

       class shipped(StateDefinition):
           description = _('Purchase shipped')

       # state transitions
       class mark_paid(StateTransition):
           from_state = 'initiated'
           to_state = 'paid'
           description = 'Mark this purchase as paid'

       class ship(StateTransition):
           from_state = 'paid'
           to_state = 'shipped'
           description = 'Ship purchase'

           def handler(transition, instance, user):
               code_to_execute_during_this_transition()

           def has_permission(transition, instance, user):
               return true_when_user_can_make_this_transition()

    class Purchase(StateModel):
        Machine = PurchaseStateMachine
        ... (other fields for a purchase)

You may of course nest the ``Machine`` class, like you would usually do
for ``Meta``.

This will create the necessary models. If ``log_transitions`` is
enabled, another model is created. Everything should be compatible with
South_ for migrations.

.. note:: If you're creating a ``DataMigration`` in South_ remember to use
  ``obj.save(no_state_validation=True)``

.. _South: http://south.aeracode.org/

Usage example::

    p = Purchase()

    # Will automatically create state object for this purchase, in the
    # initial state.
    p.save()
    p.make_transition('initiate', request.user) # User parameter is optional
    p.state # Will return 'paid'
    p.state_description # Will return 'Purchase paid'

    # Will return all the state transitions for this instance.
    p.state_transitions.all()

    # The user who triggered this transition
    p.state_transitions.all()[0].user

    # Will return 'complete' or 'failed', depending on the state of this
    # state transition.
    p.state_transitions.all()[0].state

    # Returns an iterator of possible transitions for this purchase.
    p.possible_transitions


For better transition control, override:

- ``has_permission(self, instance, user)``:
    Check whether this user is allowed to make this transition.
- ``handler(self, instance, user)``:
    Code to run during this transition. When an exception has been
    raised in here, the transition will not be made.

Get all objects in a certain state::

    Purchase.objects.filter(state='initiated')

Validation
~~~~~~~~~~
You can add a test that needs to pass before a state transition can be
executed. Well, you can add 2: one based on the current user
(``has_permission``) and one generic (``validate``).

So on a ``StateTransition``-object you need to specify an extra ``validate``
function (signature is ``validate(cls, instance)``). This should yield
``TransitionValidationError``, this way you can return multiple errors on
that need to pass before the transition can happen.

The ``has_permission`` function (signature ``has_permission(transition,
instance, user)``) should check whether the given user is allowed to make the
transition. E.g. a super user can moderate all comments while other users can
only moderate comments on their blog-posts.

Groups
~~~~~~
Sometimes you want to group several states together, since for a certain view
(or other content) it doesn't really matter which of the states it is. We
support 2 different state groups, inclusive (only these) or exclusive
(everything but these)::

      class is_paid(StateGroup):
          states = ['paid', 'shipped']

      class is_paid(StateGroup):
          exclude_states = ['initiated']

Admin actions
~~~~~~~~~~~~~
By specifying actions for the Django Admin (see `admin actions`_), you can do
state transitions for the admin site. To support this in your model, update
your ``ModelAdmin``::

    class PurchaseAdmin(admin.ModelAdmin);
        actions = Purchase.Machine.get_admin_actions()

If your model didn't inherit from ``StateModel``, you can also specify the
``field_name``::

    class PurchaseAdmin(admin.ModelAdmin);
        actions = Purchase.Machine.get_admin_actions(field_name='purchase_state')

.. _admin actions: http://docs.djangoproject.com/en/dev/ref/contrib/admin/actions/

State graph
~~~~~~~~~~~
You can get a graph of your states by running the ``graph_states`` management
command.

::

  python manage.py graph_states myapp.Purchase.state

This requires `graphviz <http://graphviz.org>`_ and python bindings for
graphviz: ``pygraphviz`` and ``yapgvb``.
