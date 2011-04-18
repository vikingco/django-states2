from states2.machine import StateMachine, StateDefinition, StateTransition


def _create_state_log_model(state_model, field_name):
    """
    Create a new model for logging the state transitions.
    """
    class StateTransitionMachine(StateMachine):
        # We don't need logging of state transitions in a state transition log entry,
        # as this would cause eternal, recursively nested state transition models.
        log_transitions = False

        class transition_initiated(StateDefinition):
            description = _('State transition initiated')
            initial = True

        class transition_started(StateDefinition):
            description = _('State transition initiated')

        class transition_failed(StateDefinition):
            description = _('State transition failed')

        class transition_completed(StateDefinition):
            description = _('State transition completed')

        class start(StateTransition):
            from_state = 'transition_initiated'
            to_state = 'transition_started'
            description = _('Start state transition')

        class complete(StateTransition):
            from_state = 'transition_started'
            to_state = 'transition_completed'
            description = _('Complete state transition')

        class fail(StateTransition):
            from_state = ('transition_initiated', 'transition_started')
            to_state = 'transition_failed'
            description = _('Mark state transition as failed')

    class _StateTransitionMeta(ModelBase):
        """
        Make _StateTransition act like it has another name,
        and was defined in another model.
        """
        def __new__(c, name, bases, attrs):
            if '__unicode__' in attrs:
                old_unicode = attrs['__unicode__']

                def new_unicode(self):
                    return '%s (%s)' % (old_unicode(self), self.Machine.get_state(self.state).description)

            attrs['__unicode__'] = new_unicode

            attrs['__module__'] = state_model.__module__
            values = {'model_name': state_model.__name__,
                      'field_name': field_name.capitalize()}
            class_name = conf.LOG_MODEL_NAME % values
            return ModelBase.__new__(c, class_name, bases, attrs)

    class _StateTransition(models.Model):
        """
        State transitions log entry.
        """
        state = StateField(max_length=64, default='0', verbose_name=_('state id'))

        from_state = models.CharField(max_length=32, choices=state_model.get_state_choices())
        to_state = models.CharField(max_length=32, choices=state_model.get_state_choices())
        user = models.ForeignKey(User, blank=True, null=True)

        start_time = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name=_('transition started at'))
        on = models.ForeignKey(state_model, related_name='all_transitions')

        Machine = StateTransitionMachine

        class Meta:
            verbose_name = _('%s transition') % state_model._meta.verbose_name

        @property
        def completed(self):
            return self.state == 'transition_completed'

        @property
        def state_transition_definition(self):
            return state_model.Machine.get_transition_from_states(self.from_state, self.to_state)

        @property
        def from_state_definition(self):
            return state_model.Machine.get_state(self.from_state)

        @property
        def from_state_description(self):
            return unicode(self.from_state_definition.description)

        @property
        def to_state_definition(self):
            return state_model.Machine.get_state(self.to_state)

        @property
        def to_state_description(self):
            return unicode(self.to_state_definition.description)

        @property
        def is_public(self):
            """
            Return True when this state transition is defined public in the machine.
            """
            return self.state_transition_definition.public

        @property
        def transition_description(self):
            """
            Return the description for this transition as defined in the
            StateTransition declaration of the machine.
            """
            return unicode(self.state_transition_definition.description)

        def __unicode__(self):
            return '<State transition on %s at %s from "%s" to "%s">' % (
                        state_model.__name__, self.start_time, self.from_state, self.to_state)

    # This model will be detected by South because of the models.Model.__new__ constructor,
    # which will register it somewhere in a global variable.

    return _StateTransition
