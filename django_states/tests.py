# -*- coding: utf-8 -*-
"""Tests"""
from __future__ import absolute_import
from django.contrib.auth.models import User
from django.db import models
from django.test import TransactionTestCase

from django_states.exceptions import (PermissionDenied, TransitionNotFound,
                                      UnknownState, UnknownTransition)
from django_states.fields import StateField
from django_states.machine import (StateDefinition, StateGroup, StateMachine,
                                   StateTransition)
from django_states.models import StateModel


class TestMachine(StateMachine):
    """A basic state machine"""
    log_transitions = False

    # States
    class start(StateDefinition):
        """Start"""
        description = "Starting State."
        initial = True

    class step_1(StateDefinition):
        """Normal State"""
        description = "Normal State"

    class step_2_fail(StateDefinition):
        """Failure State"""
        description = "Failure State"

    class step_3(StateDefinition):
        """Completed"""
        description = "Completed"

    # Transitions
    class start_step_1(StateTransition):
        """Transition from start to normal"""
        from_state = 'start'
        to_state = 'step_1'
        description = "Transition from start to normal"

    class step_1_step_2_fail(StateTransition):
        """Transition from normal to failure"""
        from_state = 'step_1'
        to_state = 'step_2_fail'
        description = "Transition from normal to failure"

    class step_1_step_3(StateTransition):
        """Transition from normal to complete"""
        from_state = 'step_1'
        to_state = 'step_3'
        description = "Transition from normal to complete"

    class step_2_fail_step_1(StateTransition):
        """Transition from failure back to normal"""
        from_state = 'step_2_fail'
        to_state = 'step_1'
        description = "Transition from failure back to normal"

    """
    GROUPS
    """
    class states_valid_start(StateGroup):
        # Valid initial states
        states = ['start', 'step_1']

    class states_error(StateGroup):
        # Error states
        states = ['step_2_fail']


class TestLogMachine(StateMachine):
    """Same as above but this one logs"""
    log_transitions = True

    # States
    class start(StateDefinition):
        """Start"""
        description = "Starting State."
        initial = True

    class first_step(StateDefinition):
        """Normal State"""
        description = "Normal State"

    class final_step(StateDefinition):
        """Completed"""
        description = "Completed"

    # Transitions
    class start_step_1(StateTransition):
        """Transition from start to normal"""
        from_state = 'start'
        to_state = 'first_step'
        description = "Transition from start to normal"
        public = True

    class step_1_final_step(StateTransition):
        """Transition from normal to complete"""
        from_state = 'first_step'
        to_state = 'final_step'
        description = "Transition from normal to complete"
        public = True

# ----- Django Test Models ------


class DjangoStateClass(StateModel):
    """Django Test Model implementing a State Machine: DEPRECATED"""
    field1 = models.IntegerField()
    field2 = models.CharField(max_length=25)
    Machine = TestMachine


class DjangoState2Class(models.Model):
    """Django Test Model implementing a State Machine used since django-states2"""
    field1 = models.IntegerField()
    field2 = models.CharField(max_length=25)

    state = StateField(machine=TestMachine)


class DjangoStateLogClass(models.Model):
    """Django Test Model implementing a Logging State Machine"""
    field1 = models.IntegerField()
    field2 = models.CharField(max_length=25)

    state = StateField(machine=TestLogMachine)

# ---- Tests ----


class StateMachineTestCase(TransactionTestCase):

    def test_initial_states(self):
        with self.assertRaises(Exception):
            class T1Machine(StateMachine):
                class start(StateDefinition):
                    description = 'start state'
                    initial = True

                class running(StateDefinition):
                    description = 'running state'
                    initial = True

        with self.assertRaises(Exception):
            class T1Machine(StateMachine):
                class start(StateDefinition):
                    description = 'start state'

                class running(StateDefinition):
                    description = 'running state'

        with self.assertRaises(Exception):
            class T1Machine(StateMachine):
                class START(StateDefinition):
                    description = 'start state'
                    initial = True

        with self.assertRaises(Exception):
            class T1Machine(StateMachine):
                class start(StateDefinition):
                    initial = True

        with self.assertRaises(Exception):
            class T1Machine(StateMachine):
                class start(StateDefinition):
                    description = 'start state'
                    initial = True

                class running(StateDefinition):
                    description = 'running state'

                class not_runing(StateGroup):
                    pass

        with self.assertRaises(Exception):
            class T1Machine(StateMachine):
                class start(StateDefinition):
                    description = 'start state'
                    initial = True

                class running(StateDefinition):
                    description = 'running state'

                class not_runing(StateGroup):
                    states = ['start']
                    exclude_states = ['running']

        with self.assertRaises(Exception):
            class T1Machine(StateMachine):
                class start(StateDefinition):
                    description = 'start state'
                    initial = True

                class running(StateDefinition):
                    description = 'running state'

                class not_runing(StateGroup):
                    states = 'start'

        with self.assertRaises(Exception):
            class T1Machine(StateMachine):
                class start(StateDefinition):
                    description = 'start state'
                    initial = True

                class running(StateDefinition):
                    description = 'running state'

                class not_runing(StateGroup):
                    exclude_states = 'running'

        with self.assertRaises(Exception):
            class T1Machine(StateMachine):
                class start(StateDefinition):
                    description = 'start state'
                    initial = True

                class running(StateDefinition):
                    description = 'running state'

                class startup(StateTransition):
                    '''Transition from stopped to running'''
                    to_state = 'running'
                    description = 'Start up the machine!'

        with self.assertRaises(Exception):
            class T1Machine(StateMachine):
                class start(StateDefinition):
                    description = 'start state'
                    initial = True

                class running(StateDefinition):
                    description = 'running state'

                class startup(StateTransition):
                    '''Transition from stopped to running'''
                    from_state = 'start'
                    from_states = ['start']
                    to_state = 'running'
                    description = 'Start up the machine!'

        with self.assertRaises(Exception):
            class T1Machine(StateMachine):
                class start(StateDefinition):
                    description = 'start state'
                    initial = True

                class running(StateDefinition):
                    description = 'running state'

                class startup(StateTransition):
                    '''Transition from stopped to running'''
                    from_state = 'start'
                    description = 'Start up the machine!'

        with self.assertRaises(Exception):
            class T1Machine(StateMachine):
                class start(StateDefinition):
                    description = 'start state'
                    initial = True

                class running(StateDefinition):
                    description = 'running state'

                class startup(StateTransition):
                    '''Transition from stopped to running'''
                    from_state = 'start'
                    to_state = 'running'

        with self.assertRaises(Exception):
            class T1Machine(StateMachine):
                class start(StateDefinition):
                    description = 'start state'
                    initial = True

                class running(StateDefinition):
                    description = 'running state'

                    def handler(self):
                        pass

        with self.assertRaises(Exception):
            class T1Machine(StateMachine):
                class start(StateDefinition):
                    description = 'start state'
                    initial = True

                class running(StateDefinition):
                    description = 'running state'

                class startup(StateTransition):
                    '''Transition from stopped to running'''
                    from_state = 'start'
                    to_state = 'running'
                    description = 'Start your engines!'

                    def handler(self, instance):
                        pass

    def test_machine_functions(self):
        class T3Machine(StateMachine):
            class stopped(StateDefinition):
                description = 'stopped state'
                initial = True

            class running(StateDefinition):
                description = 'running state'

            class crashed(StateDefinition):
                description = 'crashed state'

                def handler(self, instance):
                    pass

            class startup(StateTransition):
                '''Transition from stopped to running'''
                from_state = 'stopped'
                to_state = 'running'
                description = 'Start up the machine!'

            class working(StateGroup):
                states = ['running']

            class not_runing(StateGroup):
                exclude_states = ['running']

        self.assertTrue(T3Machine.has_state('stopped'))
        stopped = T3Machine.get_state('stopped')
        self.assertTrue(stopped.initial)
        self.assertFalse(T3Machine.has_state('died'))
        with self.assertRaises(UnknownState):
            T3Machine.get_state('died')

        self.assertTrue(T3Machine.get_state_groups('stopped')['not_runing'])
        groups = T3Machine.get_state_groups('running')
        self.assertFalse(groups['not_runing'])
        self.assertTrue(groups['working'])

        T3Machine.get_transition_from_states('stopped', 'running')
        with self.assertRaises(TransitionNotFound):
            T3Machine.get_transition_from_states('running', 'crashed')
        self.assertTrue(T3Machine.has_transition('startup'))
        self.assertFalse(T3Machine.has_transition('crash'))
        trion = T3Machine.get_transitions('startup')
        self.assertFalse(hasattr(trion, 'from_state'))
        self.assertEqual(trion.from_states[0], 'stopped')
        self.assertEqual(trion.to_state, 'running')
        with self.assertRaises(KeyError):
            T3Machine.get_transitions('crash')
        # Admin actions
        actions = T3Machine.get_admin_actions()
        self.assertEqual(len(actions), 1)
        action = actions[0]
        self.assertEqual(action.__name__, 'state_transition_startup')
        self.assertTrue('stopped' in action.short_description)
        self.assertTrue('running' in action.short_description)
        self.assertTrue('Start up the machine!' in action.short_description)


class StateFieldTestCase(TransactionTestCase):
    """This will test out the non-logging side of things"""

    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username='super', email="super@h.us", password="pass")

    def test_initial_state(self):
        """Full end to end test"""
        testclass = DjangoState2Class(field1=100, field2="LALALALALA")
        testclass.save()

        self.assertEqual(testclass.get_state_machine(), TestMachine)
        self.assertEqual(testclass.get_state_display(), 'Starting State.')

        state_info = testclass.get_state_info()

        self.assertEqual(testclass.state, 'start')
        self.assertTrue(state_info.initial)
        state_info.make_transition('start_step_1', user=self.superuser)
        self.assertFalse(state_info.initial)

    def test_end_to_end(self):
        """Full end to end test"""
        testclass = DjangoState2Class(field1=100, field2="LALALALALA")
        testclass.save()

        state_info = testclass.get_state_info()

        # Verify the starting state.
        self.assertEqual(testclass.state, 'start')
        self.assertEqual(state_info.name, testclass.state)
        self.assertEqual(state_info.description, 'Starting State.')
        possible = set([x.get_name() for x in state_info.possible_transitions])
        self.assertEqual(possible, {'start_step_1'})
        # Shift to the first state
        state_info.make_transition('start_step_1', user=self.superuser)
        self.assertEqual(state_info.name, 'step_1')
        self.assertEqual(state_info.description, 'Normal State')
        possible = set([x.get_name() for x in state_info.possible_transitions])
        self.assertEqual(possible, {'step_1_step_3', 'step_1_step_2_fail'})
        # Shift to a failure
        state_info.make_transition('step_1_step_2_fail', user=self.superuser)
        self.assertEqual(state_info.name, 'step_2_fail')
        self.assertEqual(state_info.description, 'Failure State')
        possible = set([x.get_name() for x in state_info.possible_transitions])
        self.assertEqual(possible, {'step_2_fail_step_1'})
        # Shift to a failure
        state_info.make_transition('step_2_fail_step_1', user=self.superuser)
        self.assertEqual(state_info.name, 'step_1')
        self.assertEqual(state_info.description, 'Normal State')
        possible = set([x.get_name() for x in state_info.possible_transitions])
        self.assertEqual(possible, {'step_1_step_3', 'step_1_step_2_fail'})
        # Shift to a completed
        state_info.make_transition('step_1_step_3', user=self.superuser)
        self.assertEqual(state_info.name, 'step_3')
        self.assertEqual(state_info.description, 'Completed')
        possible = [x.get_name() for x in state_info.possible_transitions]
        self.assertEqual(len(possible), 0)

    def test_invalid_user(self):
        """Verify permissions for a user"""
        user = User.objects.create(
            username='user', email="user@h.us", password="pass")

        testclass = DjangoState2Class(field1=100, field2="LALALALALA")
        testclass.save()

        kwargs = {'transition': 'start_step_1', 'user': user}

        state_info = testclass.get_state_info()

        self.assertRaises(PermissionDenied, state_info.make_transition, **kwargs)

    def test_in_group(self):
        """Tests in_group functionality"""
        testclass = DjangoState2Class(field1=100, field2="LALALALALA")
        testclass.save()

        state_info = testclass.get_state_info()

        self.assertTrue(state_info.in_group['states_valid_start'])
        state_info.make_transition('start_step_1', user=self.superuser)
        self.assertTrue(state_info.in_group['states_valid_start'])
        state_info.make_transition('step_1_step_2_fail', user=self.superuser)
        self.assertFalse(state_info.in_group['states_valid_start'])
        self.assertTrue(state_info.in_group['states_error'])
        state_info.make_transition('step_2_fail_step_1', user=self.superuser)
        self.assertTrue(state_info.in_group['states_valid_start'])
        state_info.make_transition('step_1_step_3', user=self.superuser)
        self.assertFalse(state_info.in_group['states_valid_start'])

    def test_unknown_transition(self):
        test = DjangoState2Class(field1=100, field2="LALALALALA")
        test.save()

        state_info = test.get_state_info()
        with self.assertRaises(UnknownTransition):
            state_info.make_transition('unknown_transition', user=self.superuser)

    def test_unknown_state(self):
        test = DjangoState2Class(field1=100, field2="LALALALALA")
        test.save()

        test.state = 'not-existing-state-state'
        with self.assertRaises(UnknownState):
            test.save(no_state_validation=False)
        test.state = 'not-existing-state-state2'
        test.save(no_state_validation=True)
        test.state = 'not-existing-state-state3'
        # TODO: Due to invalid default value of no_state_validation, this won't throw an error
        #with self.assertRaises(UnknownState):
        #    test.save()

    def test_state_save_handler(self):
        test = DjangoState2Class(field1=100, field2="LALALALALA")
        test.save(no_state_validation=False)


class StateModelTestCase(TransactionTestCase):
    """This will test out the non-logging side of things"""

    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username='super', email="super@h.us", password="pass")

    def test_classmethods(self):
        self.assertEqual(DjangoStateClass.get_state_model_name(),
                         'django_states.DjangoStateClass')
        state_choices = DjangoStateClass.get_state_choices()
        self.assertEqual(len(state_choices), 4)
        self.assertEqual(len(state_choices[0]), 2)
        state_choices = dict(state_choices)
        self.assertTrue('start' in state_choices)
        self.assertEqual(state_choices['start'], 'Starting State.')

    def test_model_end_to_end(self):
        test = DjangoStateClass(field1=42, field2="Knock? Knock?")
        test.save()

        self.assertEqual(test.state, 'start')
        self.assertTrue(test.is_initial_state)
        self.assertEqual(test.state_description, "Starting State.")

        self.assertEqual(len(list(test.possible_transitions)), 1)
        self.assertEqual(len(list(test.public_transitions)), 0)
        with self.assertRaises(Exception):
            test.state_transitions

        test.can_make_transition('start_step_1', user=self.superuser)
        self.assertTrue(test.is_initial_state)
        test.make_transition('start_step_1', user=self.superuser)
        self.assertFalse(test.is_initial_state)


class StateLogTestCase(TransactionTestCase):

    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username='super', email="super@h.us", password="pass")

    def test_statelog(self):
        test = DjangoStateLogClass(field1=42, field2="Hello world?")
        test.save(no_state_validation=False)

        # Verify the starting state.
        state_info = test.get_state_info()
        self.assertEqual(test.state, 'start')
        self.assertEqual(state_info.name, test.state)
        # Make transition
        state_info.make_transition('start_step_1', user=self.superuser)

        # Test whether log entry was created
        StateLogModel = DjangoStateLogClass._state_log_model
        self.assertEqual(StateLogModel.objects.count(), 1)
        entry = StateLogModel.objects.all()[0]
        self.assertTrue(entry.completed)
        # We should also be able to find this via
        self.assertEqual(test.get_state_transitions().count(), 1)
        self.assertEqual(len(test.get_public_state_transitions()), 1)
