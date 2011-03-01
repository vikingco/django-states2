
from django.db.models.fields.related import ForeignKey
from django.db import models
from functools import wraps

from states2.exceptions import *

class StateField(ForeignKey):
    """
    Statefield for a model.
    Actually a ForeignKey, but this field also makes sure that the initial
    state is automatically created after initiation of the model.
    """
        # TODO: __init__ is supposed to accept only the 'machine' argument,
        #       but south will thread this as a ForeignKey, and pass other
        #       other arguments. So, until we get our introspection rules
        #       working, also accept all the foreign key parameters.


    #def __init__(self, machine):
    def __init__(self, *args, **kwargs):
        machine = args[0] if args else kwargs['machine'] if 'machine' in kwargs else kwargs['to']
        ForeignKey.__init__(self, machine, null=False, blank=False, unique=True)
        self.machine = machine
        self.__machine_state = machine

    def contribute_to_class(self, cls, name):
        self.__name = name
        models.signals.class_prepared.connect(self.__finalize, sender=cls)

        # Call contribute_to_class of parent
        ForeignKey.contribute_to_class(self, cls, name)

    def __finalize(self, sender, **kwargs):
        # Capture set method of field descriptor
        descriptor = getattr(sender, self.name)
        self.__capture_set_method(descriptor)

        # Capture save method
        self.__capture_save_method(sender)

        # Add make_transition to the object which has a statefield
        self.__add_make_transition_method(sender)

    def __add_make_transition_method(self, sender):
        def make_transition(self, transition, user=None):
            """
            Run this state transition.
            """
            if self.state_id:
                return self.state._make_transition(transition, self, user)
            else:
                raise TransitionOnUnsavedObject(self)

        # Add 'make_transition' method to model.
        sender.make_transition = make_transition

    def __capture_set_method(self, descriptor):
        """
        A state should never be assigned by hand.
        """
            # TODO: this does not work
        def descriptor_set(self, instance, value):
            raise AttributeError("You shouldn't set the state this way.")
        descriptor.__set__ = descriptor_set

    def __capture_save_method(self, sender):
        """
        The state is created during the first save.
        """
        original_save = sender.save

        @wraps(original_save)
        def new_save(instance, *args, **kwargs):
            # If no state has been defined for this instance, save a state first.
            try:
                getattr(instance, self.__name)
            except self.__machine_state.DoesNotExist, e:
                state = self.__machine_state()
                state.save()
                setattr(instance, self.__name, state)

            # Call original save method
            original_save(instance, *args, **kwargs)

            # Save state
            pass

        sender.save = new_save


# Tell south to use introspection rules from ForeignKey for this StateField
from south.modelsinspector import add_introspection_rules
add_introspection_rules([], ["^states2\.fields\.StateField"])
#add_introspection_rules([
#    (
#        [StateField], # Class(es) these apply to
#        [],           # Positional arguments (not used)
#        {             # Keyword argument
#            "machine": ["machine", {}],
#        },
#    ),
#], [ "^states2\.fields\.StateField"])
