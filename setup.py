#!/usr/bin/env python

from os.path import exists
from setuptools import setup, find_packages

install_requires=[
    l for l in open('requirements.txt').read().strip().split('\n')
    if not l.startswith('#')
]


setup(
    name='kubernetes-informers',
    version='0.1.0-dev',
    description='Watch changes to kubernetes objects reliably',
    url='https://github.com/yuvipanda/kubernetes-informers',
    keywords='kubernetes',
    license='3-BSD',
    packages=find_packages(),
    long_description=(open('README.rst').read() if exists('README.rst') else ''),
    zip_safe=False,
    install_requires=install_requires
)
