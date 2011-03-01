
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
                # NOTE: we tell django to allow null values, but save() will make sure that
                #       a state is created. (necessary for the admin.)
        ForeignKey.__init__(self, machine, null=True, blank=True, unique=True)
        self.machine = machine
        self._state_machine = machine

    def contribute_to_class(self, cls, name):
        if name != 'state':
            raise Exception("Please call the StateField 'state' in the model where it's used")

        self._name = name
        models.signals.class_prepared.connect(self.__finalize, sender=cls)

        # Call contribute_to_class of parent
        ForeignKey.contribute_to_class(self, cls, name)

    def __finalize(self, sender, **kwargs):
        """
        The class_prepared signal is triggered when ModelBase.__new__ has finished
        creating the class where this field is used. `sender` is the class
        object (not instance) which is created in __new__.
        """
        # Capture set method of field descriptor
        descriptor = getattr(sender, self.name)
        self.__capture_set_method(descriptor)

        # Capture save method
        self.__capture_save_method(sender)

        # Wrap __unicode__ object
        self.__wrap_unicode(sender)

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

    def __wrap_unicode(self, sender):
        """
        Print state behind __unicode__
        """
        u = sender.__unicode__ if hasattr(sender, '__unicode__') else sender.__str__
        def new_unicode(o):
            return '%s (%s)' % (u(o), o.state.description)
        sender.__unicode__ = new_unicode

    def __capture_save_method(self, sender):
        """
        The state is created during the first save.
        """
        original_save = sender.save

        @wraps(original_save)
        def new_save(instance, *args, **kwargs):
            # If no state has been defined for this instance, save a state first.
            if not getattr(instance, 'state'):
                state = self._state_machine()
                state.save()
                setattr(instance, self._name, state)

            # Call original save method
            original_save(instance, *args, **kwargs)

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
