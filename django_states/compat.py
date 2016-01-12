from __future__ import absolute_import
# Django >= 1.4 moves handler404, handler500, include, patterns and url from
# django.conf.urls.defaults to django.conf.urls.
try:
        from django.conf.urls import (patterns, url, include)
except ImportError:
        from django.conf.urls.defaults import (patterns, url, include)
