#!/usr/bin/env python
import os

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

setup(
    name='nuage_amp',
    version='0.1.2',
    packages=['nuage_amp', 'nuage_amp.utils', 'nuage_amp.operations'],
    data_files=[('/etc/nuage-amp', ['config/nuage-amp.conf']),
                ('/usr/bin', ['config/nuage-amp']),
                ('/etc/init.d', ['config/nuage-amp-sync'])],
    url='https://github.com/nuagecommunity/nuage-amp',
    license='Apache V2.0',
    author='Philippe Jeurissen',
    author_email='philippe@nuagenetworks.com',
    description='Nuage Advanced Management Portal(AMP)',
    classifiers=(
        'Development Status :: 5 - Production/Stable',
        'Environment :: OpenStack',
        'Intended Audience :: Information Technology',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: Apache Software License',
        'Natural Language :: English',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
    ),
)
