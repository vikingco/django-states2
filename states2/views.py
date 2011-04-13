from django.http import HttpResponseRedirect, HttpResponseForbidden, HttpResponse

from states2.utils import get_state_model
from states2.exceptions import PermissionDenied


def make_state_transition(request):
    if request.method == 'POST':
        model = get_state_model(request.POST['model_name'])
        instance = model.objects.get(id=request.POST['id'])
        action = request.POST['action']

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
