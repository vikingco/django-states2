from django.db.models import get_model
from django.http import HttpResponseRedirect, HttpResponseForbidden, HttpResponse

from states2.exceptions import PermissionDenied


def make_state_transition(request):
    if request.method == 'POST':
        app_label, model_name = request.POST['model_name'].split('.')
        model = get_model(app_label, model_name)
        instance = model.objects.get(id=request.POST['id'])
        action = request.POST['action']

        if not hasattr(instance, 'make_transition'):
            raise Exception('No such state model "%s"' % model_name)

        try:
            # Make state transition
            instance.make_transition(action, request.user)

            # ... Redirect to 'next'
            if 'next' in request.REQUEST:
                return HttpResponseRedirect(request.REQUEST['next'])
            else:
                return HttpResponse('OK')

        except PermissionDenied, e:
            return HttpResponseForbidden()

    else:
        return HttpResponseForbidden()
