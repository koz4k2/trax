# coding=utf-8
# Copyright 2019 The Trax Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Install trax."""

from setuptools import find_packages
from setuptools import setup

setup(
    name='trax',
    version='1.0.1',
    description='Trax',
    author='Google Inc.',
    author_email='no-reply@google.com',
    url='http://github.com/google/trax',
    license='Apache 2.0',
    packages=find_packages(),
    install_requires=[
        'gin-config',
        'gym',
        'numpy',
        'scipy',
        'six',
        'jax',
        'jaxlib',
        'tensor2tensor',
        'tensorflow-datasets',
        'absl-py',
    ],
    extras_require={
        'tensorflow': ['tensorflow>=1.14.0'],
        'tensorflow_gpu': ['tensorflow-gpu>=1.14.0'],
        'tests': [
            'attrs',
            'pytest',
            'mock',
            'pylint',
            'jupyter',
            'matplotlib',
        ],
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: Apache Software License',
        'Topic :: Scientific/Engineering :: Artificial Intelligence',
    ],
    keywords='tensorflow machine learning jax',
)
