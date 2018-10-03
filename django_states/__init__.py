# -*- coding: utf-8 -*-
"""
State engine for django models.

Define a state graph for a model and remember the state of each object.
State transitions can be logged for objects.
"""
from __future__ import absolute_import

__name__ = 'django_states'
__author__ = 'Pivotal Energy Solutions'
__version_info__ = (1, 6, 14)
__version__ = '.'.join(map(str, __version_info__))
__date__ = '2014/07/22 4:47:00 PM'
__credits__ = ['Jonathan Slenders', 'Ben Mason', 'Dirk Moors', 'Gert Van Gool', 'Giovanni Collazo', 'Jakub Paczkowski',
               'Jan Fabry', 'Jef Geskens', 'Jonathan Slenders', 'José Padilla', 'Linsy Aerts',
               'Maarten Timmerman', 'Niels Van Och', 'Olivier Sels', 'OpenShift guest', 'San Gillis',
               'Simon Andersson', 'Steven Klass', 'sgillis', 'techdragon',]
__license__ = 'See the file LICENSE.txt for licensing information.'
