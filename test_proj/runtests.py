#!/usr/bin/env python

import os
import sys

os.environ['DJANGO_SETTINGS_MODULE'] = 'test_proj.settings'

sys.path.insert(0, os.path.dirname(__file__))

import django
from django.conf import settings
from django.test.utils import get_runner

def main():
    if hasattr(django, 'setup'):
        django.setup()

    TestRunner = get_runner(settings)
    test_runner = TestRunner(verbosity=1, interactive=False)
    failures = test_runner.run_tests(['django_states',])
    sys.exit(1 if failures else 0)

if __name__ == '__main__':
    main()
