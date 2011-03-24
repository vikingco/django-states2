===========================================================
Django States (v2)
===========================================================

Author: Jonathan Slenders, City Live nv

Description:

    State engine for django models. Define a state graph for
    a model and remember the state of each object.
    State transitions can be logged for objects.



Usage example:

    It's basically these two things:
    - Derived your model from StateModel
    - Add a Machine class to your model, for the state machine


    >  from states2.models import StateModel, StateMachine, StateDefinition, StateTransition
    >
    >  class PurchaseStateMachine(StateMachine):
    >     log_transitions = True
    >
    >
    >     class initiated(StateDefinition):
    >         description = _('Purchase initiated')
    >         initial = True
    >
    >     class paid(StateDefinition):
    >         description = _('Purchase paid')
    >
    >     class shipped(StateDefinition):
    >         description = _('Purchase shipped')
    >
    >
    >     class mark_paid(StateTransition):
    >         from_state = 'initiated'
    >         to_state = 'paid'
    >         description = 'Mark this purchase as paid'
    >
    >     class ship(StateTransition):
    >         from_state = 'paid'
    >         to_state = 'shipped'
    >         description = 'Ship purchase'
    >
    >         def handler(transition, instance, user):
    >             code_to_execute_during_this_transition()
    >
    >         def has_permission(transition, instance, user):
    >             return true_when_user_can_make_this_transition()
    >
    >  class Purchase(StateModel):
    >      Machine = PurchaseStateMachine
    >      ... (other fields for a purchase)


    You may of course nest the Machine class, like you would usually do for Meta.

    This will create the necessary models. if `log_transitions` is enabled, another models
    is created. Everything should be compatible with South.


    Usage example:

    p = Purchase()
    p.save()   # Will automatically create state object for this purchase, in the initial state.
    p.make_transition('initiate')
    p.state # Will return 'paid'
    p.state_description # Will return 'Purchase paid'
    p.state_transitions.all() # Will return all the state transitions for this instance.
    p.state_transitions.all()[0].user # The user who triggered this transition
    p.state_transitions.all()[0].state # Will return 'complete' or 'failed', depending
                            # on the state of this state transition.
    p.possible_transitions # Returns an iterator of possible transitions for this purchase.
    

    For better transition control, override:

        - has_permission(self, instance, user):
            Check whether this user is allowed to make this transition.

        - handler(self, instance, user):
            Code to run during this transition. When an exception has been
            raised in here, the transition will not be made.


    Get all objects in a certain state:

    >  Purchase.objects.filter(state='initiated') 


    Actions for the Django Admin:

    >   class PurchaseAdmin(admin.ModelAdmin);
    >       actions = Purchase.Machine.get_admin_actions()
