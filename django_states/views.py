# -*- coding: utf-8 -*-
"""Views"""
from __future__ import absolute_import

from django.db.models import get_model
from django.http import (HttpResponseRedirect, HttpResponseForbidden,
                         HttpResponse,)
from django.shortcuts import get_object_or_404

from django_states.exceptions import PermissionDenied


def make_state_transition(request):
    """
    View to be called by AJAX code to do state transitions. This must be a
    ``POST`` request.

    Required parameters:

    - ``model_name``: the name of the state model, as retured by
      ``instance.get_state_model_name``.
    - ``action``: the name of the state transition, as given by
      ``StateTransition.get_name``.
    - ``id``: the ID of the instance on which the state transition is applied.

    When the handler requires additional kwargs, they can be passed through as
    optional parameters: ``kwarg-{{ kwargs_name }}``
    """
    if request.method == 'POST':
        # Process post parameters
        app_label, model_name = request.POST['model_name'].split('.')
        try:
            model = get_model(app_label, model_name)
        except LookupError:
            model = None
        instance = get_object_or_404(model, id=request.POST['id'])
        action = request.POST['action']

        # Build optional kwargs
        kwargs = {}
        for p in request.POST:
            if p.startswith('kwarg-'):
                kwargs[p[len('kwargs-')-1:]] = request.POST[p]

        if not hasattr(instance, 'make_transition'):
            raise Exception('No such state model "%s"' % model_name)

        try:
            # Make state transition
            instance.make_transition(action, request.user, **kwargs)
        except PermissionDenied as e:
            return HttpResponseForbidden()
        else:
            # ... Redirect to 'next'
            if 'next' in request.POST:
                return HttpResponseRedirect(request.POST['next'])
            else:
                return HttpResponse('OK')
    else:
        return HttpResponseForbidden()
