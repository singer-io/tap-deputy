#!/usr/bin/env python

from setuptools import setup

setup(name='tap-deputy',
      version='1.1.3',
      description='Singer.io tap for extracting data from the Deputy API',
      author='Deputy',
      url='https://www.deputy.com',
      classifiers=['Programming Language :: Python :: 3 :: Only'],
      python_requires='>=3.5.3',
      py_modules=['tap_deputy'],
      install_requires=[
          'backoff==1.10.0',
          'requests==2.32.4',
          'singer-python==5.13.2'
      ],
      extras_require= {
          'dev': [
              'pylint',
              'nose',
              'ipdb',
          ]
      },
      entry_points='''
          [console_scripts]
          tap-deputy=tap_deputy:main
      ''',
      packages=['tap_deputy']
)
