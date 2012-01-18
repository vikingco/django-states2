from django.conf.urls.defaults import patterns, url
from states2.views import make_state_transition

urlpatterns = patterns('',
    url(r'^make-state-transition/$', make_state_transition, name='states2_make_transition'),
)
