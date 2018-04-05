#!/usr/bin/env python

from setuptools import setup


with open('README.md') as f:
    long_description = f.read()

setup(name='shredder',
      version=.7,
      description='Simple multiprocessing',
      long_description=long_description,
      url='http://github.com/svrana/shredder',
      author='Shaw Vrana',
      author_email='shaw@vranix.com',
      license='MIT',
      packages=['shredder'],
      classifiers=[
        'License :: OSI Approved :: MIT License',
      ],
      install_requires=[
      ],
      zip_safe=False,
)
