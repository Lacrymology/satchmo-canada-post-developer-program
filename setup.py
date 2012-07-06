#!/usr/bin/env python

from setuptools import find_packages, setup

setup(
    name='satchmo-canada-post-development-program',
    version='0.0.0',
    author='Tomas Neme',
    url='http://github.com/Lacrymology',
    description = ("Shipping module for satchmo that uses the new Developer "
                   "Program from Canada Post"),
    packages=find_packages(),
    install_requires = [
        'git+git://github.com/Lacrymology/python-canada-post-dev-prog'
    ],
    include_package_data=True,
)
