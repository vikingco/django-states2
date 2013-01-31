# -*- coding: utf-8 -*-
"""
State engine for django models.

Define a state graph for a model and remember the state of each object.
State transitions can be logged for objects.
"""

#: The version list
VERSION = (1, 5, 0)

#: The actual version number, used by python (and shown in sentry)
__version__ = '.'.join(map(str, VERSION))
