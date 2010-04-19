try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

import os
readme_file = os.path.join(os.path.dirname(__file__),
                           'README')
long_description = open(readme_file).read()    

setup(name='django-crowdsourcing',
      version='1.1',
      description='Django app for collecting and displaying surveys.',
      long_description=long_description,
      author='Jacob Smullyan, Dave Smith',
      author_email='jsmullyan@gmail.com',
      url='http://code.google.com/p/django-crowdsourcing/',
      packages=['crowdsourcing'],
      license='MIT',
     )
