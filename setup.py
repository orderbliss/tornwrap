#!/usr/bin/env python
from setuptools import setup

classifiers = ["Development Status :: 4 - Beta",
               "Environment :: Plugins",
               "Intended Audience :: Developers",
               "License :: OSI Approved :: Apache Software License",
               "Topic :: Software Development :: Testing"]

with open('requirements.txt', 'r') as f:
    requirements = f.readlines()

setup(name='tornwrap',
      version="0.0.1",
      description="tornadoweb decorator",
      long_description=None,
      classifiers=classifiers,
      keywords='tornado tornadoweb decorators wrapper',
      author='@stevepeak',
      author_email='steve@stevepeak.net',
      url='http://github.com/stevepeak/tornwrap',
      license='http://www.apache.org/licenses/LICENSE-2.0',
      packages=['tornwrap'],
      package_data=None,
      include_package_data=True,
      zip_safe=True,
      install_requires=requirements,
      entry_points=None)
