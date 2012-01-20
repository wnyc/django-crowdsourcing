try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

import os
readme_file = os.path.join(os.path.dirname(__file__),
                           'README')
long_description = open(readme_file).read()

classifiers = [
    'Development Status :: 4 - Beta',
    'Framework :: Django',
    'License :: OSI Approved :: MIT License']


setup(name='django-crowdsourcing',
      version='1.1.31',
      classifiers=classifiers,
      description='Django app for collecting and displaying surveys.',
      long_description=long_description,
      author='Jacob Smullyan, Dave Smith',
      author_email='jsmullyan@gmail.com',
      url='http://code.google.com/p/django-crowdsourcing/',
      packages=['crowdsourcing', 'crowdsourcing.templatetags'],
      license='MIT',
     )
