# -*- coding: utf-8 -*-
from setuptools import setup

setup(
    name='python-dwca-reader',
    version='0.13.1',
    author=u'Nicolas Noé - Belgian Biodiversity Platform',
    author_email='n.noe@biodiversity.be',
    packages=['dwca', 'dwca.darwincore', 'dwca.test'],
    url="https://github.com/BelgianBiodiversityPlatform/python-dwca-reader",
    license='BSD licence, see LICENCE.txt',
    description='A simple Python package to read Darwin Core Archive (DwC-A) files.',
    long_description=open('README.rst').read(),
    install_requires=[
        'typing;python_version<"3.5"',
    ],
    classifiers=[
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7'
    ]
)
