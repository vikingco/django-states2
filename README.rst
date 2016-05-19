Django States
=============

|Build Status|

Description
-----------

State engine for django models. Define a state graph for a model and
remember the state of each object. State transitions can be logged for
objects.

Installation
------------

.. code:: sh

    pip install django-states

Usage example
-------------

To use a state machine, you should add a state field to the model

.. code:: python

    from django_states.fields import StateField
    from django_states.machine import StateMachine, StateDefinition, StateTransition

    class PurchaseStateMachine(StateMachine):
       log_transitions = True

       # possible states
       class initiated(StateDefinition):
           description = _('Purchase initiated')
           initial = True

           def handler(self, instance):
               # To execute code in this handler make sure to save the instance with
               # obj.save(no_state_validation=False) on object creation
               code_to_execute_when_arriving_in_this_state()

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

           def handler(transition, instance, user, **kwargs):
               code_to_execute_during_this_transition()

           def has_permission(transition, instance, user):
               return true_when_user_can_make_this_transition()

    class Purchase(StateModel):
        purchase_state = StateField(machine=PurchaseStateMachine, default='initiated')
        ... (other fields for a purchase)

If ``log_transitions`` is enabled, another model is created. Everything
should be compatible with South\_ for migrations.

Usage example:

.. code:: python

   p = Purchase()

   # Will automatically create state object for this purchase, in the
   # initial state.
   p.save()
   p.get_purchase_state_info().make_transition('mark_paid', request.user) # User parameter is optional
   p.state # Will return 'paid'
   p.get_purchase_state_info().description # Will return 'Purchase paid'

   # Returns an iterator of possible transitions for this purchase.
   p.get_purchase_state_info().possible_transitions()

   # Which can be used like this..
   [x.get_name() for x in p.possible_transitions]

For better transition control, override:

-  ``has_permission(self, instance, user)``: Check whether this user is
   allowed to make this transition. See: `Validation`_
-  ``validate(self, instance)``: Check whether this transition is
   allowed. See: `Validation`_
-  ``handler(self, instance, user, **kwargs)``: Code to run during this
   transition. When an exception has been raised in here, the transition
   will not be made. See: `Handlers`_

Get all objects in a certain state::

   Purchase.objects.filter(state='initiated')

Validation
----------

You can add a test that needs to pass before a state transition can be
executed. Well, you can add 2: one based on the current user
(``has_permission``) and one generic (``validate``).

So on a ``StateTransition``-object you need to specify an extra
``validate`` function (signature is ``validate(cls, instance)``). This
should yield ``TransitionValidationError``, this way you can return
multiple errors on that need to pass before the transition can happen.

The ``has_permission`` function (signature
``has_permission(transition, instance, user)``) should check whether the
given user is allowed to make the transition. E.g. a super user can
moderate all comments while other users can only moderate comments on
their blog-posts.

Handlers
--------

You can execute code upon doing a state transition or when reaching a
certain state.

For executing code when reaching a certain state add a ``handler`` function
(signature is ``handler(cls, instance)``) to your ``StateDefinition``. When
this state is reached successfully the code in the handler is executed. To
execute the code in the handler of the initial state (``StateDefinition`` with
``initial = True``) make sure that you save the created object using
``obj.save(no_state_validation=False)`` (``no_state_validation`` defaults to ``True``).

To execute code when doing a certain state transition add a ``handler`` function
(signature is ``handler(cls, instance, user, **kwargs)``) to your ``StateTransition``.
This code is only executed when the state transition is allowed.

Example:

.. code:: python

   class ModerationMachine(StateMachine):
      """A simple state machine for moderating articles"""

      # States
      class pending(StateDefinition):
         description = 'Pending review'
         initial = True

         def handler(cls, instance):
            # When a new article is added a manager should review it, so email
            # all managers to notify them about the new article
            mail_managers(
               'New article pending review: {}'.format(instance.title),
               'Empty message')

      class approved(StateDefinition):
         description = 'Approved'

         def handler(cls, instance):
            send_mail(
               'Your article has been approved',
               'Empty message',
               'from@example.com',
               [instance.author.email])

      class rejected(StateDefinition):
         description = 'Rejected'

      # State transitions
      class reject(StateTransition):
         from_states = ['pending']
         to_state = 'rejected'
         description = 'Reject submitted article'

         def handler(cls, instance, user, reason):
            # The handler in the StateTransition can also be used,
            # and can receive additional **kwargs from a state transition
            # in this case to relay a reason for rejection
            send_mail(
               'Your article has been rejected',
               'Reason for rejection: {}'.format(reason),
               'from@example.com',
               [instance.author.email])

      class approve(StateTransition):
         from_states = ['pending']
         to_state = 'approved'
         description = 'Approve submitted article'


   class Article(models.Model):
      title = models.CharField(max_length=100)
      author = models.ForeignKey(User)

      state = StateField(machine=ModerationMachine)


   # Example code:
   author = User.objects.create_user('Erik', 'erik@example.org', 'mypassword')
   article = Article(title='Using migrations in Django', author=author)
   article.save(no_state_validation=False)
   # Email is send to all managers notifying them of a new article pending review
   article.get_state_info().make_transition('reject', reason='Improper writing style')
   # Email is send to the author detailing the reason for rejection

.. note::

   If you're creating a ``DataMigration`` in
   `South <http://south.aeracode.org/>`__, remember to use
   ``obj.save(no_state_validation=True)``

Groups
------

Sometimes you want to group several states together, since for a certain
view (or other content) it doesn't really matter which of the states it
is. We support 2 different state groups, inclusive (only these) or
exclusive (everything but these):

.. code:: python

  class is_paid(StateGroup):
      states = ['paid', 'shipped']

  class is_paid(StateGroup):
      exclude_states = ['initiated']

State graph
-----------

You can get a graph of your states by running the ``graph_states``
management command.

.. code:: sh

   python manage.py graph_states myapp.Purchase.state

This requires `graphviz <http://graphviz.org>`__ and python bindings for
graphviz: ``pygraphviz`` and ``yapgvb``.

.. |Build Status| image:: https://travis-ci.org/vikingco/django-states2.svg?branch=fix%2F15403%2Fdebug-in_group-and-add-unittests
   :target: https://travis-ci.org/vikingco/django-states2
