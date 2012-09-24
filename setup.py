#!/usr/bin/env python


from setuptools import setup

setup (
    name='ptools',
    version='1.0b1',
    description='Cross Platform Process Infomation (cmdline, environ) and Management',
    author='The Test People',
    author_email='tony.simpson@thetestpeople.com',
    maintainer='Tony Simpson',
    license='MIT',
    packages=['ptools'],
    long_description=open('README.md').read(),
)

