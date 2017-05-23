from setuptools import setup, find_packages

def readme():
    with open("README.md", 'r') as f:
        return f.read()

setup(
    name = "qremis_api",
    description = "A web API for managing a (PREMIS-like) qremis database",
    long_description = readme(),
    packages = find_packages(
        exclude = [
        ]
    ),
    dependency_links = [
        'https://github.com/bnbalsamo/pyqremis' +
        '/tarball/master#egg=pyqremis'
    ],
    install_requires = [
        'flask>0',
        'flask_restful',
        'redis',
        'pymongo',
        'pyqremis'
    ],
)
