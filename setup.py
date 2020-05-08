#!/usr/bin/env python
# Copyright 2020 Juan Manuel Mera
# Distributed under the terms of GNU General Public License v3 (GPLv3)

from setuptools import setup

with open('README.md') as f:
    long_description = f.read()

setup(
    name='rads2file',
    version='0.1.0',
    description='Convert RAR Alternate Data Streams to Files',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='Juan Mera',
    author_email='juanmera@gmail.com',
    url='https://www.github.com/juanmera/ctf',
    packages=['rads2file'],
    install_requires=['rarfile'],
    entry_points={
        'console_scripts': ['rads2file=rads2file.main:main']
    }
)
