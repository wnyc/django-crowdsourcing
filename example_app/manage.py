#!/usr/bin/env python
import os, sys

# to be able to import the crowdsourcing app
sys.path.append(os.path.normpath(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "example_app.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

