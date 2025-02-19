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

"""Core class and functions for handling data abstractly as shapes/dtypes."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import numpy as onp


class ShapeDtype(object):
  """A NumPy ndarray-like object abstracted as shape and dtype."""
  __slots__ = ['shape', 'dtype']

  def __init__(self, shape, dtype=onp.float32):
    self.shape = shape
    self.dtype = dtype

  def __repr__(self):
    return 'ShapeDtype{{shape:{}, dtype:{}}}'.format(self.shape, self.dtype)


def shape_dtype_for(obj):
  """Returns a `ShapeDtype` instance with the shape and dtype of `obj`."""
  return ShapeDtype(obj.shape, obj.dtype)
