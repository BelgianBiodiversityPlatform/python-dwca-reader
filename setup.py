from setuptools import setup

exec(open("dwca/version.py").read())

setup(
    name="python-dwca-reader",
    version=__version__,  # type: ignore
    author="Nicolas Noé - Belgian Biodiversity Platform",
    author_email="n.noe@biodiversity.be",
    packages=["dwca", "dwca.darwincore", "dwca.test"],
    url="https://github.com/BelgianBiodiversityPlatform/python-dwca-reader",
    license="BSD licence, see LICENCE.txt",
    description="A simple Python package to read Darwin Core Archive (DwC-A) files.",
    long_description=open("README.rst").read(),
    long_description_content_type="text/x-rst",
    python_requires=">=3.8",
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Programming Language :: Python :: Implementation :: PyPy",
    ],
)
