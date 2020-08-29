# -*- coding: utf-8 -*-
from __future__ import division, print_function, absolute_import

import setuptools  # required to allow for use of python setup.py develop, may also be important for cython/compiling if it is used

from distutils.core import setup



setup(
    name="pingodraw",
    version="0.1.0",
    description="""platform independent drawing""",
    author="""Chris Lee-Messer""",
    url="https://github.com/eegml/pingo-drawing",
    classifiers=["Topic :: Graphics"],
    packages=["pingodraw"],
    #install_requires = [],
    # package_data={}
    # data_files=[],
    # scripts = [],
)
