# -*- coding: utf-8 -*-
from distutils.core import setup

setup(
    name='python-dwca-reader',
    version='0.12.0',
    author=u'Nicolas Noé - Belgian Biodiversity Platform',
    author_email='n.noe@biodiversity.be',
    packages=['dwca', 'dwca.darwincore', 'dwca.test'],
    url="https://github.com/BelgianBiodiversityPlatform/python-dwca-reader",
    license='BSD licence, see LICENCE.txt',
    description='A simple Python package to read Darwin Core Archive (DwC-A) files.',
    long_description=open('README.rst').read(),
    classifiers=[
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6'
    ]
)
