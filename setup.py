from setuptools import setup

exec(open('dwca/version.py').read())

setup(
    name='python-dwca-reader',
    version= __version__,
    author=u'Nicolas Noé - Belgian Biodiversity Platform',
    author_email='n.noe@biodiversity.be',
    packages=['dwca', 'dwca.darwincore', 'dwca.test'],
    url="https://github.com/BelgianBiodiversityPlatform/python-dwca-reader",
    license='BSD licence, see LICENCE.txt',
    description='A simple Python package to read Darwin Core Archive (DwC-A) files.',
    long_description=open('README.rst').read(),
    classifiers=[
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8'
    ]
)
