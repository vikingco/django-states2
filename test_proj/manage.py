#!/usr/bin/env python
import os, sys
from django.core.management import execute_from_command_line

if not 'DJANGO_SETTINGS_MODULE' in os.environ:
    os.environ["DJANGO_SETTINGS_MODULE"] = "settings"

if __name__ == "__main__":
    execute_from_command_line(argv=sys.argv[0:])
