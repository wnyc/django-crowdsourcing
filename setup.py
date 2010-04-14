try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

setup(name='Crowdsourcing',
      version='1.0',
      description='Django app for collecting and displaying surveys.',
      author='Jacob Smullyan, Dave Smith',
      author_email='jsmullyan@gmail.com',
      url='http://code.google.com/p/django-crowdsourcing/',
      packages=['crowdsourcing'],
     )
