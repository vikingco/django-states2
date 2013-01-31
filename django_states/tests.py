# -*- coding: utf-8 -*-
"""Tests"""
from django.contrib.auth.models import User

from django.db import models
from django.test import TransactionTestCase
from django_states.exceptions import PermissionDenied
from django_states.machine import StateMachine, StateDefinition, StateTransition
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


#class TestLogMachine(TestMachine):
#    """Same as above but this one logs"""
#    log_transitions = True

# ----- Django Test Models ------


class DjangoStateClass(StateModel):
    """Django Test Model implementing a State Machine"""
    field1 = models.IntegerField()
    field2 = models.CharField(max_length=25)
    Machine = TestMachine


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
        testmachine = DjangoStateClass(field1=100, field2="LALALALALA")
        testmachine.save()
        self.assertEqual(testmachine.state, 'start')
        self.assertTrue(testmachine.is_initial_state)
        testmachine.make_transition('start_step_1', user=self.superuser)
        self.assertFalse(testmachine.is_initial_state)

    def test_end_to_end(self):
        """Full end to end test"""
        testmachine = DjangoStateClass(field1=100, field2="LALALALALA")
        testmachine.save()
        # Verify the starting state.
        self.assertEqual(testmachine.state, 'start')
        self.assertEqual(testmachine.state_description, 'Starting State.')
        possible = set([x.get_name() for x in testmachine.possible_transitions])
        self.assertEqual(possible, {'start_step_1'})
        # Shift to the first state
        testmachine.make_transition('start_step_1', user=self.superuser)
        self.assertEqual(testmachine.state, 'step_1')
        self.assertEqual(testmachine.state_description, 'Normal State')
        possible = set([x.get_name() for x in testmachine.possible_transitions])
        self.assertEqual(possible, {'step_1_step_3', 'step_1_step_2_fail'})
        # Shift to a failure
        testmachine.make_transition('step_1_step_2_fail', user=self.superuser)
        self.assertEqual(testmachine.state, 'step_2_fail')
        self.assertEqual(testmachine.state_description, 'Failure State')
        possible = set([x.get_name() for x in testmachine.possible_transitions])
        self.assertEqual(possible, {'step_2_fail_step_1'})
        # Shift to a failure
        testmachine.make_transition('step_2_fail_step_1', user=self.superuser)
        self.assertEqual(testmachine.state, 'step_1')
        self.assertEqual(testmachine.state_description, 'Normal State')
        possible = set([x.get_name() for x in testmachine.possible_transitions])
        self.assertEqual(possible, {'step_1_step_3', 'step_1_step_2_fail'})
        # Shift to a completed
        testmachine.make_transition('step_1_step_3', user=self.superuser)
        self.assertEqual(testmachine.state, 'step_3')
        self.assertEqual(testmachine.state_description, 'Completed')
        possible = [x.get_name() for x in testmachine.possible_transitions]
        self.assertEqual(len(possible), 0)

    def test_invalid_user(self):
        """Verify permissions for a user"""
        user = User.objects.create(
            username='user', email="user@h.us", password="pass")
        testmachine = DjangoStateClass(field1=100, field2="LALALALALA")
        testmachine.save()
        kwargs = {'transition': 'start_step_1', 'user': user}
        self.assertRaises(PermissionDenied, testmachine.make_transition, **kwargs)
