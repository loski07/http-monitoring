from setuptools import setup, find_packages
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

# Get python dependencies from the requirements file
with open(path.join(here, 'requirements.txt'), encoding='utf-8') as f:
    install_requires = f.read()

setup(
    name='http_monitor',
    version='1.0',
    description='Program that monitors an http log and alerts on conditions',
    long_description=long_description,

    url='https://github.com/loski07/http-monitoring',
    author='Pablo Díaz <loski07@gmail.com>',

    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Recruiting',
        'Programming Language :: Python :: 3.10'
    ],

    keywords='http monitor',

    packages=find_packages(exclude=['docs', 'tests']),

    install_requires=install_requires,

    entry_points={
        'console_scripts': [
            'http_monit = http_monit.runner:main',
        ],
    }
)
