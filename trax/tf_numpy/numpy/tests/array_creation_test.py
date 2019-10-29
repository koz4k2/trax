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

"""Tests for tf-numpy array creation methods."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import itertools
import numpy as np
import tensorflow
import tensorflow.compat.v2 as tf

from trax.tf_numpy.numpy import array_creation
from trax.tf_numpy.numpy import arrays


class ArrayCreationTest(tf.test.TestCase):

  def setUp(self):
    super(ArrayCreationTest, self).setUp()
    python_shapes = [
        0, 1, 2, (), (1,), (2,), (1, 2, 3), [], [1], [2], [1, 2, 3]
    ]
    self.shape_transforms = [
        lambda x: x, lambda x: np.array(x, dtype=int),
        lambda x: array_creation.array(x, dtype=int), tf.TensorShape
    ]

    self.all_shapes = []
    for fn in self.shape_transforms:
      self.all_shapes.extend([fn(s) for s in python_shapes])

    self.all_types = [
        int, float, np.int16, np.int32, np.int64, np.float16, np.float32,
        np.float64
    ]

    source_array_data = [
        1,
        5.5,
        7,
        (),
        (8, 10.),
        ((), ()),
        ((1, 4), (2, 8)),
        [],
        [7],
        [8, 10.],
        [[], []],
        [[1, 4], [2, 8]],
        ([], []),
        ([1, 4], [2, 8]),
        [(), ()],
        [(1, 4), (2, 8)],
    ]

    self.array_transforms = [
        lambda x: x,
        tf.convert_to_tensor,
        np.array,
        array_creation.array,
    ]
    self.all_arrays = []
    for fn in self.array_transforms:
      self.all_arrays.extend([fn(s) for s in source_array_data])

  def testEmpty(self):
    for s in self.all_shapes:
      actual = array_creation.empty(s)
      expected = np.empty(s)
      msg = 'shape: {}'.format(s)
      self.match_shape(actual, expected, msg)
      self.match_dtype(actual, expected, msg)

    for s, t in itertools.product(self.all_shapes, self.all_types):
      actual = array_creation.empty(s, t)
      expected = np.empty(s, t)
      msg = 'shape: {}, dtype: {}'.format(s, t)
      self.match_shape(actual, expected, msg)
      self.match_dtype(actual, expected, msg)

  def testEmptyLike(self):
    for a in self.all_arrays:
      actual = array_creation.empty_like(a)
      expected = np.empty_like(a)
      msg = 'array: {}'.format(a)
      self.match_shape(actual, expected, msg)
      self.match_dtype(actual, expected, msg)

    for a, t in itertools.product(self.all_arrays, self.all_types):
      actual = array_creation.empty_like(a, t)
      expected = np.empty_like(a, t)
      msg = 'array: {} type: {}'.format(a, t)
      self.match_shape(actual, expected, msg)
      self.match_dtype(actual, expected, msg)

  def testZeros(self):
    for s in self.all_shapes:
      actual = array_creation.zeros(s)
      expected = np.zeros(s)
      msg = 'shape: {}'.format(s)
      self.match(actual, expected, msg)

    for s, t in itertools.product(self.all_shapes, self.all_types):
      actual = array_creation.zeros(s, t)
      expected = np.zeros(s, t)
      msg = 'shape: {}, dtype: {}'.format(s, t)
      self.match(actual, expected, msg)

  def testZerosLike(self):
    for a in self.all_arrays:
      actual = array_creation.zeros_like(a)
      expected = np.zeros_like(a)
      msg = 'array: {}'.format(a)
      self.match(actual, expected, msg)

    for a, t in itertools.product(self.all_arrays, self.all_types):
      actual = array_creation.zeros_like(a, t)
      expected = np.zeros_like(a, t)
      msg = 'array: {} type: {}'.format(a, t)
      self.match(actual, expected, msg)

  def testOnes(self):
    for s in self.all_shapes:
      actual = array_creation.ones(s)
      expected = np.ones(s)
      msg = 'shape: {}'.format(s)
      self.match(actual, expected, msg)

    for s, t in itertools.product(self.all_shapes, self.all_types):
      actual = array_creation.ones(s, t)
      expected = np.ones(s, t)
      msg = 'shape: {}, dtype: {}'.format(s, t)
      self.match(actual, expected, msg)

  def testOnesLike(self):
    for a in self.all_arrays:
      actual = array_creation.ones_like(a)
      expected = np.ones_like(a)
      msg = 'array: {}'.format(a)
      self.match(actual, expected, msg)

    for a, t in itertools.product(self.all_arrays, self.all_types):
      actual = array_creation.ones_like(a, t)
      expected = np.ones_like(a, t)
      msg = 'array: {} type: {}'.format(a, t)
      self.match(actual, expected, msg)

  def testEye(self):
    n_max = 3
    m_max = 3

    for n in range(1, n_max + 1):
      self.match(array_creation.eye(n), np.eye(n))
      for k in range(-n, n + 1):
        self.match(array_creation.eye(n, k=k), np.eye(n, k=k))
      for m in range(1, m_max + 1):
        self.match(array_creation.eye(n, m), np.eye(n, m))
        for k in range(-n, m):
          self.match(array_creation.eye(n, k=k), np.eye(n, k=k))
          self.match(array_creation.eye(n, m, k), np.eye(n, m, k))

    for dtype in self.all_types:
      for n in range(1, n_max + 1):
        self.match(array_creation.eye(n, dtype=dtype), np.eye(n, dtype=dtype))
        for k in range(-n, n + 1):
          self.match(
              array_creation.eye(n, k=k, dtype=dtype),
              np.eye(n, k=k, dtype=dtype))
        for m in range(1, m_max + 1):
          self.match(
              array_creation.eye(n, m, dtype=dtype), np.eye(n, m, dtype=dtype))
          for k in range(-n, m):
            self.match(
                array_creation.eye(n, k=k, dtype=dtype),
                np.eye(n, k=k, dtype=dtype))
            self.match(
                array_creation.eye(n, m, k, dtype=dtype),
                np.eye(n, m, k, dtype=dtype))

  def testIdentity(self):
    n_max = 3

    for n in range(1, n_max + 1):
      self.match(array_creation.identity(n), np.identity(n))

    for dtype in self.all_types:
      for n in range(1, n_max + 1):
        self.match(
            array_creation.identity(n, dtype=dtype), np.identity(
                n, dtype=dtype))

  def testFull(self):
    # List of 2-tuples of fill value and shape.
    data = [
        (5, ()),
        (5, (7,)),
        (5., (7,)),
        ([5, 8], (2,)),
        ([5, 8], (3, 2)),
        ([[5], [8]], (2, 3)),
        ([[5], [8]], (3, 2, 5)),
        ([[5.], [8.]], (3, 2, 5)),
        ([[3, 4], [5, 6], [7, 8]], (3, 3, 2)),
    ]
    for f, s in data:
      for fn1, fn2 in itertools.product(self.array_transforms,
                                        self.shape_transforms):
        fill_value = fn1(f)
        shape = fn2(s)
        self.match(
            array_creation.full(shape, fill_value), np.full(shape, fill_value))
        for dtype in self.all_types:
          self.match(
              array_creation.full(shape, fill_value, dtype=dtype),
              np.full(shape, fill_value, dtype=dtype))

  def testFullLike(self):
    # List of 2-tuples of fill value and shape.
    data = [
        (5, ()),
        (5, (7,)),
        (5., (7,)),
        ([5, 8], (2,)),
        ([5, 8], (3, 2)),
        ([[5], [8]], (2, 3)),
        ([[5], [8]], (3, 2, 5)),
        ([[5.], [8.]], (3, 2, 5)),
    ]
    zeros_builders = [array_creation.zeros, np.zeros]
    for f, s in data:
      for fn1, fn2, arr_dtype in itertools.product(
          self.array_transforms, zeros_builders, self.all_types):
        fill_value = fn1(f)
        arr = fn2(s, arr_dtype)
        self.match(
            array_creation.full_like(arr, fill_value),
            np.full_like(arr, fill_value))
        for dtype in self.all_types:
          self.match(
              array_creation.full_like(arr, fill_value, dtype=dtype),
              np.full_like(arr, fill_value, dtype=dtype))

  def testArray(self):
    ndmins = [0, 1, 2, 5]
    for a, dtype, ndmin, copy in itertools.product(
        self.all_arrays, self.all_types, ndmins, [True, False]):
      self.match(
          array_creation.array(a, dtype=dtype, ndmin=ndmin, copy=copy),
          np.array(a, dtype=dtype, ndmin=ndmin, copy=copy))

    zeros_list = array_creation.zeros(5)

    # TODO(srbs): Test that copy=True when context.device is different from
    # tensor device copies the tensor.

    # Backing tensor is the same if copy=False, other attributes being None.
    self.assertIs(
        array_creation.array(zeros_list, copy=False).data, zeros_list.data)
    self.assertIs(
        array_creation.array(zeros_list.data, copy=False).data, zeros_list.data)

    # Backing tensor is different if ndmin is not satisfied.
    self.assertIsNot(
        array_creation.array(zeros_list, copy=False, ndmin=2).data,
        zeros_list.data)
    self.assertIsNot(
        array_creation.array(zeros_list.data, copy=False, ndmin=2).data,
        zeros_list.data)
    self.assertIs(
        array_creation.array(zeros_list, copy=False, ndmin=1).data,
        zeros_list.data)
    self.assertIs(
        array_creation.array(zeros_list.data, copy=False, ndmin=1).data,
        zeros_list.data)

    # Backing tensor is different if dtype is not satisfied.
    self.assertIsNot(
        array_creation.array(zeros_list, copy=False, dtype=int).data,
        zeros_list.data)
    self.assertIsNot(
        array_creation.array(zeros_list.data, copy=False, dtype=int).data,
        zeros_list.data)
    self.assertIs(
        array_creation.array(zeros_list, copy=False, dtype=float).data,
        zeros_list.data)
    self.assertIs(
        array_creation.array(zeros_list.data, copy=False, dtype=float).data,
        zeros_list.data)

  def testAsArray(self):
    for a, dtype in itertools.product(self.all_arrays, self.all_types):
      self.match(
          array_creation.asarray(a, dtype=dtype), np.asarray(a, dtype=dtype))

    zeros_list = array_creation.zeros(5)
    # Same instance is returned if no dtype is specified and input is ndarray.
    self.assertIs(array_creation.asarray(zeros_list), zeros_list)
    # Different instance is returned if dtype is specified and input is ndarray.
    self.assertIsNot(array_creation.asarray(zeros_list, dtype=int), zeros_list)

  def testAsAnyArray(self):
    for a, dtype in itertools.product(self.all_arrays, self.all_types):
      self.match(
          array_creation.asanyarray(a, dtype=dtype),
          np.asanyarray(a, dtype=dtype))
    zeros_list = array_creation.zeros(5)
    # Same instance is returned if no dtype is specified and input is ndarray.
    self.assertIs(array_creation.asanyarray(zeros_list), zeros_list)
    # Different instance is returned if dtype is specified and input is ndarray.
    self.assertIsNot(
        array_creation.asanyarray(zeros_list, dtype=int), zeros_list)

  def testAsContiguousArray(self):
    for a, dtype in itertools.product(self.all_arrays, self.all_types):
      self.match(
          array_creation.ascontiguousarray(a, dtype=dtype),
          np.ascontiguousarray(a, dtype=dtype))

  def testARange(self):
    int_values = np.arange(-3, 3).tolist()
    float_values = np.arange(-3.5, 3.5).tolist()
    all_values = int_values + float_values
    for dtype in self.all_types:
      for start in all_values:
        msg = 'dtype:{} start:{}'.format(dtype, start)
        self.match(array_creation.arange(start), np.arange(start), msg=msg)
        self.match(
            array_creation.arange(start, dtype=dtype),
            np.arange(start, dtype=dtype),
            msg=msg)
        for stop in all_values:
          msg = 'dtype:{} start:{} stop:{}'.format(dtype, start, stop)
          self.match(
              array_creation.arange(start, stop),
              np.arange(start, stop),
              msg=msg)
          # TODO(srbs): Investigate and remove check.
          # There are some bugs when start or stop is float and dtype is int.
          if not isinstance(start, float) and not isinstance(stop, float):
            self.match(
                array_creation.arange(start, stop, dtype=dtype),
                np.arange(start, stop, dtype=dtype),
                msg=msg)
          # Note: We intentionally do not test with float values for step
          # because numpy.arange itself returns inconsistent results. e.g.
          # np.arange(0.5, 3, step=0.5, dtype=int) returns
          # array([0, 1, 2, 3, 4])
          for step in int_values:
            msg = 'dtype:{} start:{} stop:{} step:{}'.format(
                dtype, start, stop, step)
            if not step:
              with self.assertRaises(ValueError):
                self.match(
                    array_creation.arange(start, stop, step),
                    np.arange(start, stop, step),
                    msg=msg)
                if not isinstance(start, float) and not isinstance(stop, float):
                  self.match(
                      array_creation.arange(start, stop, step, dtype=dtype),
                      np.arange(start, stop, step, dtype=dtype),
                      msg=msg)
            else:
              self.match(
                  array_creation.arange(start, stop, step),
                  np.arange(start, stop, step),
                  msg=msg)
              if not isinstance(start, float) and not isinstance(stop, float):
                self.match(
                    array_creation.arange(start, stop, step, dtype=dtype),
                    np.arange(start, stop, step, dtype=dtype),
                    msg=msg)

  def testLinSpace(self):
    array_transforms = [
        lambda x: x,  # Identity,
        tf.convert_to_tensor,
        np.array,
        lambda x: np.array(x, dtype=np.float32),
        lambda x: np.array(x, dtype=np.float64),
        array_creation.array,
        lambda x: array_creation.array(x, dtype=np.float32),
        lambda x: array_creation.array(x, dtype=np.float64)
    ]

    def run_test(start, stop, **kwargs):
      for fn1 in array_transforms:
        for fn2 in array_transforms:
          arg1 = fn1(start)
          arg2 = fn2(stop)
          self.match(
              array_creation.linspace(arg1, arg2, **kwargs),
              np.linspace(arg1, arg2, **kwargs),
              msg='linspace({}, {})'.format(arg1, arg2),
              almost=True)

    run_test(0, 1)
    run_test(0, 1, num=10)
    run_test(0, 1, endpoint=False)
    run_test(0, -1)
    run_test(0, -1, num=10)
    run_test(0, -1, endpoint=False)

  def testLogSpace(self):
    array_transforms = [
        lambda x: x,  # Identity,
        tf.convert_to_tensor,
        np.array,
        lambda x: np.array(x, dtype=np.float32),
        lambda x: np.array(x, dtype=np.float64),
        array_creation.array,
        lambda x: array_creation.array(x, dtype=np.float32),
        lambda x: array_creation.array(x, dtype=np.float64)
    ]

    def run_test(start, stop, **kwargs):
      for fn1 in array_transforms:
        for fn2 in array_transforms:
          arg1 = fn1(start)
          arg2 = fn2(stop)
          self.match(
              array_creation.logspace(arg1, arg2, **kwargs),
              np.logspace(arg1, arg2, **kwargs),
              msg='logspace({}, {})'.format(arg1, arg2),
              almost=True)

    run_test(0, 5)
    run_test(0, 5, num=10)
    run_test(0, 5, endpoint=False)
    run_test(0, 5, base=2.0)
    run_test(0, -5)
    run_test(0, -5, num=10)
    run_test(0, -5, endpoint=False)
    run_test(0, -5, base=2.0)

  def testGeomSpace(self):

    def run_test(start, stop, **kwargs):
      arg1 = start
      arg2 = stop
      self.match(
          array_creation.geomspace(arg1, arg2, **kwargs),
          np.geomspace(arg1, arg2, **kwargs),
          msg='geomspace({}, {})'.format(arg1, arg2),
          almost=True,
          decimal=4)

    run_test(1, 1000, num=5)
    run_test(1, 1000, num=5, endpoint=False)
    run_test(-1, -1000, num=5)
    run_test(-1, -1000, num=5, endpoint=False)

  def testDiag(self):
    array_transforms = [
        lambda x: x,  # Identity,
        tf.convert_to_tensor,
        np.array,
        lambda x: np.array(x, dtype=np.float32),
        lambda x: np.array(x, dtype=np.float64),
        array_creation.array,
        lambda x: array_creation.array(x, dtype=np.float32),
        lambda x: array_creation.array(x, dtype=np.float64)
    ]

    def run_test(arr):
      for fn in array_transforms:
        arr = fn(arr)
        self.match(
            array_creation.diag(arr), np.diag(arr), msg='diag({})'.format(arr))
        for k in range(-3, 3):
          self.match(
              array_creation.diag(arr, k),
              np.diag(arr, k),
              msg='diag({}, k={})'.format(arr, k))

    # 2-d arrays.
    run_test(np.arange(9).reshape((3, 3)).tolist())
    run_test(np.arange(6).reshape((2, 3)).tolist())
    run_test(np.arange(6).reshape((3, 2)).tolist())
    run_test(np.arange(3).reshape((1, 3)).tolist())
    run_test(np.arange(3).reshape((3, 1)).tolist())
    run_test([[5]])
    run_test([[]])
    run_test([[], []])

    # 1-d arrays.
    run_test([])
    run_test([1])
    run_test([1, 2])

  def testDiagFlat(self):
    array_transforms = [
        lambda x: x,  # Identity,
        tf.convert_to_tensor,
        np.array,
        lambda x: np.array(x, dtype=np.float32),
        lambda x: np.array(x, dtype=np.float64),
        array_creation.array,
        lambda x: array_creation.array(x, dtype=np.float32),
        lambda x: array_creation.array(x, dtype=np.float64)
    ]

    def run_test(arr):
      for fn in array_transforms:
        arr = fn(arr)
        self.match(
            array_creation.diagflat(arr),
            np.diagflat(arr),
            msg='diagflat({})'.format(arr))
        for k in range(-3, 3):
          self.match(
              array_creation.diagflat(arr, k),
              np.diagflat(arr, k),
              msg='diagflat({}, k={})'.format(arr, k))

    # 1-d arrays.
    run_test([])
    run_test([1])
    run_test([1, 2])
    # 2-d arrays.
    run_test([[]])
    run_test([[5]])
    run_test([[], []])
    run_test(np.arange(4).reshape((2, 2)).tolist())
    run_test(np.arange(2).reshape((2, 1)).tolist())
    run_test(np.arange(2).reshape((1, 2)).tolist())
    # 3-d arrays
    run_test(np.arange(8).reshape((2, 2, 2)).tolist())

  def match_shape(self, actual, expected, msg=None):
    if msg:
      msg = 'Shape match failed for: {}. Expected: {} Actual: {}'.format(
          msg, expected.shape, actual.shape)
    self.assertEqual(actual.shape, expected.shape, msg=msg)
    if msg:
      msg = 'Shape: {} is not a tuple for {}'.format(actual.shape, msg)
    self.assertIsInstance(actual.shape, tuple, msg=msg)

  def match_dtype(self, actual, expected, msg=None):
    if msg:
      msg = 'Dtype match failed for: {}. Expected: {} Actual: {}.'.format(
          msg, expected.dtype, actual.dtype)
    self.assertEqual(actual.dtype, expected.dtype, msg=msg)

  def match(self, actual, expected, msg=None, almost=False, decimal=7):
    msg_ = 'Expected: {} Actual: {}'.format(expected, actual)
    if msg:
      msg = '{} {}'.format(msg_, msg)
    else:
      msg = msg_
    self.assertIsInstance(actual, arrays.ndarray)
    self.match_dtype(actual, expected, msg)
    self.match_shape(actual, expected, msg)
    if not almost:
      if not actual.shape:
        self.assertEqual(actual.tolist(), expected.tolist())
      else:
        self.assertSequenceEqual(actual.tolist(), expected.tolist())
    else:
      np.testing.assert_almost_equal(
          actual.tolist(), expected.tolist(), decimal=decimal)

  def testIndexedSlices(self):
    dtype = tf.int64
    iss = tf.IndexedSlices(values=tf.ones([2, 3], dtype=dtype),
                           indices=tf.constant([1, 9]),
                           dense_shape=[10, 3])
    a = array_creation.array(iss, copy=False)
    expected = tf.scatter_nd([[1], [9]], tf.ones([2, 3], dtype=dtype), [10, 3])
    self.assertAllEqual(expected, a)


if __name__ == '__main__':
  tensorflow.compat.v1.enable_eager_execution()
  tf.test.main()
