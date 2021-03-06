#!/usr/bin/env python

from setuptools import find_packages, setup
VERSION = "0.1.0-2"

setup(
    name='satchmo-canada-post-developer-program',
    version=VERSION,
    author='Tomas Neme',
    url='http://github.com/Lacrymology/satchmo-canada-post-developer-program',
    description = ("Shipping module for satchmo that uses the new Developer "
                   "Program from Canada Post"),
    packages=find_packages(),
    install_requires = [
        'django-jsonfield',
    ],
    include_package_data=True,
)
