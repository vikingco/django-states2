# -*- coding: utf-8 -*-
"""Tests"""
from django.contrib.auth.models import User

from django.db import models
from django.test import TransactionTestCase
from django_states.exceptions import PermissionDenied
from django_states.fields import StateField
from django_states.machine import StateMachine, StateDefinition, StateTransition, StateGroup
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
        #Valid initial states
        states = ['start', 'step_1']

    class states_error(StateGroup):
        #Error states
        states = ['step_2_fail']

#class TestLogMachine(TestMachine):
#    """Same as above but this one logs"""
#    log_transitions = True

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


#class DjangoStateLogClass(models.Model):
#    """Django Test Model implementing a Logging State Machine"""
#    field1 = models.IntegerField()
#    field2 = models.CharField(max_length=25)
#    Machine = TestLogMachine

# ---- Tests ----


class StateTestCase(TransactionTestCase):
    """This will test out the non-logging side of things"""

    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username='super', email="super@h.us", password="pass")

    def test_initial_state(self):
        """Full end to end test"""
        testclass = DjangoState2Class(field1=100, field2="LALALALALA")
        testclass.save()

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