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

"""Transformer Models."""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import jax

from trax import backend
from trax import layers as tl
from trax.layers.combinators import _pop_rng_and_split


# Layers are always CamelCase, but functions in general are snake_case
# pylint: disable=invalid-name


class Map(tl.Layer):
  """Combinator for applying a layer to a list or tuple."""

  def __init__(self, layer, n_sections=1, check_shapes=True):
    """Initialize the combinator.

    Args:
      layer: a layer to apply to each element.
      n_sections: how many sections to map to (default: 1).
      check_shapes: whether to check that shapes are identical (default: true).

    Returns:
      A new layer representing mapping layer to all elements of the input.
    """
    super(Map, self).__init__(n_in=n_sections, n_out=n_sections)
    if layer is None or isinstance(layer, (list, tuple)):
      layer = tl.Serial(layer)
    self._layer = layer
    # Generally a Map should be applied to lists where all elements have
    # the same shape -- because self._layer will only be initialized once
    # and it could have different parameters for different shapes. But there
    # are valid cases -- e.g., when self._layer has no parameters -- where we
    # can apply Map to different shapes -- set check_shapes=False in such cases.
    self._check_shapes = check_shapes
    self._n_sections = n_sections

  def forward(self, inputs, params=(), state=(), **kwargs):
    if self._n_sections == 1:
      results = self._layer(inputs, params=params, state=state, **kwargs)
    else:
      rngs = _pop_rng_and_split(kwargs, len(inputs))
      results = [self._layer(x, params=params, state=state, rng=r, **kwargs)
                 for x, r in zip(inputs, rngs)]
      results = tuple(results)
    # TODO(kitaev): think about how to merge state across copies in the map.
    return results, self._layer.state

  def new_params_and_state(self, input_shape, input_dtype, rng):
    if self._n_sections == 1:
      return self._layer.initialize_once(input_shape, input_dtype, rng)
    first_shape = input_shape[0]
    if self._check_shapes:
      for shape in input_shape:
        if shape != first_shape:
          raise ValueError('Map layer can only be applied to list of elements '
                           'with the same shapes. This shape %s vs first shape '
                           '%s.' % (str(shape), str(first_shape)))
    return self._layer.initialize_once(first_shape, input_dtype[0], rng)

  @tl.Layer.params.setter
  def params(self, params):
    self._params = self._layer.params = params

  @tl.Layer.state.setter
  def state(self, state):
    self._state = self._layer.state = state


@tl.layer()
def BroadcastedDropout(x, params, rate=0.0, mode='train', broadcast_dims=(-2,),
                       rng=None, **kwargs):
  """Dropout, with broadcasting to save memory."""
  del params, kwargs
  if rng is None:
    raise ValueError('BroadcastedDropout requires rng kwarg.')
  if rate >= 1.0:
    raise ValueError('Dropout rate (%f) must be lower than 1.' % rate)
  if mode == 'train' and rate > 0.0:
    noise_shape = list(x.shape)
    for dim in broadcast_dims:
      noise_shape[dim] = 1
    keep_prob = jax.lax.tie_in(rng, 1.0 - rate)
    keep = backend.random.bernoulli(rng, keep_prob, tuple(noise_shape))
    multiplier = keep.astype(x.dtype) / jax.lax.tie_in(keep, keep_prob)
    return x * multiplier
  else:
    return x


def FeedForward(d_model, d_ff, dropout, mode):
  """Feed-forward block with layer normalization at start."""
  return [
      tl.LayerNorm(),
      tl.Dense(d_ff),
      BroadcastedDropout(rate=dropout, mode=mode),  # pylint: disable=no-value-for-parameter
      tl.Relu(),
      tl.Dense(d_model),
      BroadcastedDropout(rate=dropout, mode=mode),  # pylint: disable=no-value-for-parameter
  ]


class SplitForOutput(tl.ReversibleLayer):
  """Splits activations into sections (for use right before the output layer).

  After the reversible portion of the network, there is a final output portion
  that's non-reversible (which at minimum includes normalization, output
  projection, and log-softmax). The output portion needs to operate on chunks
  of the sequence to avoid running out of memory for large vocabulary sizes.

  This layer concatenates the two subparts of the activations along the feature
  dimension, and then splits into chunks along the time dimension. We implement
  it is a subclass of tl.ReversibleLayer because we want to ensure that multiple
  copies of the activations don't exist simultaneously except in the middle of a
  memory copy operation.
  """

  def __init__(self, n_sections=2, axis=-2):
    super(SplitForOutput, self).__init__(n_in=2, n_out=n_sections)
    self._n_sections = n_sections
    self._axis = axis

  def forward(self, inputs, params=(), state=(), **kwargs):
    del params, kwargs
    x1, x2 = inputs

    x1_split = backend.numpy.split(x1, self._n_sections, self._axis)
    x2_split = backend.numpy.split(x2, self._n_sections, self._axis)

    res = [backend.numpy.concatenate(ys, -1) for ys in zip(x1_split, x2_split)]
    return tuple(res), state

  def reverse(self, output, params=(), state=(), **kwargs):
    del params, kwargs

    x1_split = []
    x2_split = []
    for y in output:
      y1, y2 = backend.numpy.split(y, 2, -1)
      x1_split.append(y1)
      x2_split.append(y2)

    x1 = backend.numpy.concatenate(x1_split, self._axis)
    x2 = backend.numpy.concatenate(x2_split, self._axis)

    return (x1, x2)

  def reverse_and_grad(self, output, ct, params=(), state=(), **kwargs):
    del params, kwargs
    return self.reverse(output), (self.reverse(ct), ())


@tl.layer()
def Chunk(x, params, n_sections=2, **kwargs):
  del params, kwargs
  assert x.shape[1] % n_sections == 0
  return backend.numpy.reshape(x, (
      x.shape[0] * n_sections,
      x.shape[1] // n_sections,
      ) + x.shape[2:])


@tl.layer()
def Unchunk(x, params, n_sections=2, **kwargs):
  del params, kwargs
  assert x.shape[0] % n_sections == 0
  return backend.numpy.reshape(x, (
      x.shape[0] // n_sections,
      x.shape[1] * n_sections,
      ) + x.shape[2:])


class ReversibleHalfResidual(tl.ReversibleLayer, tl.Serial):
  """Half of a RevNet-style residual (only updates part of the hidden state)."""

  def __init__(self, residual_layers):
    self.compute_residual = tl.Serial(
        # (x1_or_y1, x2) -> (x2, x1_or_y1, x2)
        tl.Parallel([], tl.Dup()),
        tl.Swap(),
        tl.Parallel(residual_layers, [], []),
    )

    layers = [
        self.compute_residual,
        tl.Parallel(tl.Add(), [])
    ]
    super(ReversibleHalfResidual, self).__init__(layers)

    self.subtract_top = tl.Parallel(tl.SubtractTop(), [])
    self.reverse_layers = [self.compute_residual, self.subtract_top]

  def reverse(self, output, params=(), state=(), **kwargs):
    reconstructed_x = output
    rng = kwargs.pop('rng', None)
    rngs = (None,) * self._n_layers
    if rng is not None:
      rngs = backend.random.split(rng, self._n_layers)
    # Note that self.sublayers aligns exactly with self.reverse_layers in
    # terms of parameter and rng usage, so no re-ordering is required.
    for layer, p, s, rng in zip(self.reverse_layers, params, state, rngs):
      reconstructed_x = layer(reconstructed_x, params=p, state=s, rng=rng,
                              **kwargs)
    return reconstructed_x

  def reverse_and_grad(self, output, ct, params=(), state=(), **kwargs):
    rng = kwargs.pop('rng', None)
    rngs = (None,) * self._n_layers
    if rng is not None:
      rngs = backend.random.split(rng, self._n_layers)

    def call_compute_residual(x, params):
      res = self.compute_residual(x, params=params, state=state[0], rng=rngs[0],
                                  **kwargs)
      return res

    assert len(ct) == 2
    ct = ((ct[0], ct[0], ct[1]))

    stack_with_residual, vjpfun = jax.vjp(
        call_compute_residual, output, params[0])
    reconstructed_x = self.subtract_top(
        stack_with_residual, params=params[-1], state=state[-1], rng=rngs[-1],
        **kwargs)

    x_ct, residual_params_ct = vjpfun(ct)
    assert not jax.tree_util.tree_leaves(params[-1])
    add_top_params_ct = params[-1]
    return reconstructed_x, (x_ct, [residual_params_ct, add_top_params_ct])


class ApplyAttentionWrapper(tl.Parallel):
  """Like tl.Parallel(attention, [], []) but implements forward_and_backward."""

  def __init__(self, attention):
    assert hasattr(attention, 'forward_and_backward')
    super(ApplyAttentionWrapper, self).__init__(attention, [], [])
    self.attention = attention

  def forward_and_backward(self, inputs, ct, rng=None, **kwargs):
    # Simultaneous forward pass and backprop through the attention mechanism.
    qkv = inputs[:3]
    passthrough = inputs[3:]
    out_ct = ct[0]
    passthrough_ct = ct[1:]
    if rng is not None:
      # Adjust RNG to match the forward pass.
      rng = backend.random.split(rng, self._n_layers)[0]

    out, qkv_ct = self.attention.forward_and_backward(
        qkv, out_ct, rng=rng, **kwargs)
    return (out,) + passthrough, qkv_ct + passthrough_ct


class ReversibleAttentionHalfResidual(tl.ReversibleLayer, tl.Serial):
  """Half of a RevNet-style residual that performs attention.

  If inputs are (x1, x2), then outputs are (x1 + z, x2) where:
  z = post_attention(attention(pre_attention(x1)))

  Other than an efficiency optimization, this layer is equivalent to
  ReversibleHalfResidual([pre_attention, attention, post_attention]).

  The post_attention layers must be linear in their input (typically they will
  consists of reshaping and dense linear layers), which allows the following
  optimization. We can back-propagate the gradient signal from the output of
  ReversibleAttentionHalfResidual to the output of the "attention" portion based
  only on the network parameters. Then, attention.forward_and_backward can be
  used to recover the output of the "attention" portion while simultaneously
  performing the backward pass, which allows shared computation between the two
  directions.
  """

  def __init__(self, pre_attention, attention, post_attention):
    self.pre_attention = tl.Serial(
        # (x1_or_y1, x2) -> (x2, x1_or_y1, x2)
        tl.Parallel([], tl.Dup()),
        tl.Swap(),
        tl.Parallel(pre_attention, [], []),
    )
    assert hasattr(attention, 'forward_and_backward')
    self.attention = ApplyAttentionWrapper(attention)
    self.post_attention = tl.Parallel(post_attention, [], [])

    layers = [
        self.pre_attention,
        self.attention,
        self.post_attention,
        tl.Parallel(tl.Add(), []),
    ]
    super(ReversibleAttentionHalfResidual, self).__init__(layers)

    self.subtract_top = tl.Parallel(tl.SubtractTop(), [])
    self.reverse_layers = [
        self.pre_attention,
        self.attention,
        self.post_attention,
        self.subtract_top,
    ]

  def reverse(self, output, params=(), state=(), **kwargs):
    rng = kwargs.pop('rng', None)
    rngs = (None,) * self._n_layers
    if rng is not None:
      rngs = backend.random.split(rng, self._n_layers)

    reconstructed_x = output
    # Note that self.sublayers aligns exactly with self.reverse_layers in
    # terms of parameter and rng usage, so no re-ordering is required.
    for layer, p, s, rng in zip(self.reverse_layers, params, state, rngs):
      reconstructed_x = layer.reverse(reconstructed_x, params=p, state=s,
                                      rng=rng, **kwargs)
    return reconstructed_x

  def reverse_and_grad(self, output, ct, params=(), state=(), **kwargs):
    rng = kwargs.pop('rng', None)
    rngs = (None,) * self._n_layers
    if rng is not None:
      rngs = backend.random.split(rng, self._n_layers)

    # Forward pass through self.pre_attention, while preparing for
    # later backprop.
    def call_pre_attention(x, params):
      res = self.pre_attention(x, params=params, state=state[0], rng=rngs[0],
                               **kwargs)
      return res
    stack, pre_attention_vjpfun = jax.vjp(call_pre_attention, output, params[0])

    # Backprop through adding the residual
    assert len(ct) == 2
    ct = saved_ct = (ct[0], ct[0], ct[1])

    # Backprop through self.post_attention with respect to the inputs only
    def call_post_attention(x):
      res = self.post_attention(x, params=params[2], state=state[2],
                                rng=rngs[2], **kwargs)
      return res
    # Note: these are *not* the actual inputs to self.post_attention.
    # If self.post_attention is not linear, we will get incorrect gradients.
    dummy_inputs = (stack[-3], stack[-2], stack[-1])
    _, post_attention_vjpfun = jax.vjp(call_post_attention, dummy_inputs)
    (ct,) = post_attention_vjpfun(ct)

    # Simultaneous forward pass and backprop through the attention mechanism
    stack, ct = self.attention.forward_and_backward(stack, ct, rng=rngs[1],
                                                    **kwargs)
    assert not jax.tree_util.tree_leaves(params[1])
    attention_params_ct = params[1]  # This is valid when params is empty.

    # Backprop through self.pre_attention
    x_ct, pre_attention_params_ct = pre_attention_vjpfun(ct)

    # Forward pass for self.post_attention, and backprop with respect to the
    # parameters only
    def call_post_attention2(params):
      res = self.post_attention(stack, params=params, state=state[2],
                                rng=rngs[2], **kwargs)
      return res
    stack, post_attention_vjpfun = jax.vjp(call_post_attention2, params[2])
    (post_attention_params_ct,) = post_attention_vjpfun(saved_ct)

    # Forward pass through subtracting the residual
    reconstructed_x = self.subtract_top(
        stack, params=params[-1], state=state[-1], rng=rngs[-1], **kwargs)

    assert not jax.tree_util.tree_leaves(params[-1])
    add_top_params_ct = params[-1]
    params_ct = [
        pre_attention_params_ct,
        attention_params_ct,
        post_attention_params_ct,
        add_top_params_ct,
    ]

    return reconstructed_x, (x_ct, params_ct)


def DecoderBlock(d_model, d_ff, d_attention_key, d_attention_value,
                 n_heads, n_attention_chunks, attention_type,
                 dropout, share_qk, mode):
  """Reversible transformer decoder layer.

  Args:
    d_model: int:  depth of embedding
    d_ff: int: depth of feed-forward layer
    d_attention_key: int: depth of key vector for each attention head
    d_attention_value: int: depth of value vector for each attention head
    n_heads: int: number of attention heads
    n_attention_chunks: int: number of chunks for attention
    attention_type: subclass of tl.BaseCausalAttention: attention class to use
    dropout: float: dropout rate (how much to drop out)
    share_qk: string, whether to share queries and keys
    mode: str: 'train' or 'eval'

  Returns:
    the layer.
  """
  if share_qk:
    pre_attention = [
        Chunk(n_sections=n_attention_chunks),  # pylint: disable=no-value-for-parameter
        tl.LayerNorm(),
        tl.Dup(),
        tl.Parallel(
            tl.ComputeAttentionHeads(n_heads=n_heads, d_head=d_attention_key),
            tl.ComputeAttentionHeads(n_heads=n_heads, d_head=d_attention_value),
        ),
        tl.Dup(),
    ]
  else:
    pre_attention = [
        Chunk(n_sections=n_attention_chunks),  # pylint: disable=no-value-for-parameter
        tl.LayerNorm(),
        tl.Dup(), tl.Dup(),
        tl.Parallel(
            tl.ComputeAttentionHeads(n_heads=n_heads, d_head=d_attention_key),
            tl.ComputeAttentionHeads(n_heads=n_heads, d_head=d_attention_key),
            tl.ComputeAttentionHeads(n_heads=n_heads, d_head=d_attention_value),
        ),
    ]

  attention = attention_type(mode=mode)

  # ReversibleAttentionHalfResidual requires that post_attention be linear in
  # its input (so the backward pass can be computed without knowing the input)
  post_attention = [
      tl.ComputeAttentionOutput(n_heads=n_heads, d_model=d_model),
      Unchunk(n_sections=n_attention_chunks),  # pylint: disable=no-value-for-parameter
      BroadcastedDropout(rate=dropout, mode=mode),  # pylint: disable=no-value-for-parameter
  ]

  feed_forward = [
      FeedForward(d_model, d_ff, dropout, mode=mode),
  ]
  return [
      ReversibleAttentionHalfResidual(pre_attention, attention, post_attention),
      tl.ReversibleSwap(),
      ReversibleHalfResidual(feed_forward),
      tl.ReversibleSwap(),
  ]


def ReformerLM(vocab_size,
               d_model=512,
               d_ff=2048,
               d_attention_key=64,
               d_attention_value=64,
               n_layers=6,
               n_heads=8,
               dropout=0.1,
               max_len=2048,
               n_chunks=0,
               n_attention_chunks=1,
               attention_type=tl.DotProductCausalAttention,
               share_qk=False,
               axial_pos_shape=(),
               d_axial_pos_embs=None,
               mode='train'):
  """Reversible transformer language model (only uses a decoder, no encoder).

  Args:
    vocab_size: int: vocab size
    d_model: int:  depth of *each half* of the two-part features
    d_ff: int: depth of feed-forward layer
    d_attention_key: int: depth of key vector for each attention head
    d_attention_value: int: depth of value vector for each attention head
    n_layers: int: number of decoder layers
    n_heads: int: number of attention heads
    dropout: float: dropout rate (how much to drop out)
    max_len: int: maximum symbol length for positional encoding
    n_chunks: int: number of chunks (must match input pipeline)
    n_attention_chunks: int: number of chunks for attention
    attention_type: class: attention class to use, such as DotProductAttention.
    share_qk: bool, whether to share queries and keys.
    axial_pos_shape: tuple of ints: input shape to use for the axial position
      encoding. If unset, axial position encoding is disabled.
    d_axial_pos_embs: tuple of ints: depth of position embedding for each axis.
      Tuple length must match axial_pos_shape, and values must sum to d_model.
    mode: str: 'train' or 'eval'

  Returns:
    the layer.
  """
  if n_chunks == 0:
    n_chunks = 1
    concatenate_input_chunks = []
  else:
    concatenate_input_chunks = tl.Concatenate(n_items=n_chunks)

  if not axial_pos_shape:
    positional_encoding = tl.PositionalEncoding(
        max_len=max_len, dropout=dropout)
  else:
    assert d_axial_pos_embs is not None
    positional_encoding = tl.AxialPositionalEncoding(
        shape=axial_pos_shape, d_embs=d_axial_pos_embs,
        dropout_broadcast_dims=tuple(range(1, len(axial_pos_shape) + 1)),
        dropout=dropout)

  positional_embedder = [
      tl.Embedding(d_model, vocab_size),
      BroadcastedDropout(rate=dropout, mode=mode),  # pylint: disable=no-value-for-parameter
      positional_encoding,
  ]

  decoder_blocks = []

  if isinstance(attention_type, (tuple, list)):
    assert n_layers % len(attention_type) == 0
  else:
    attention_type = [attention_type]
  for layer_idx in range(n_layers):
    layer_attention_type = attention_type[layer_idx % len(attention_type)]
    decoder_block = DecoderBlock(
        d_model, d_ff, d_attention_key, d_attention_value, n_heads,
        n_attention_chunks,
        attention_type=layer_attention_type,
        dropout=dropout,
        share_qk=(share_qk or issubclass(layer_attention_type,
                                         tl.LSHCausalAttention)),
        mode=mode)
    decoder_blocks.append(decoder_block)

  return tl.Serial(
      concatenate_input_chunks,
      tl.ShiftRight(),
      positional_embedder,
      tl.Dup(),
      tl.ReversibleSerial(decoder_blocks + [
          SplitForOutput(n_sections=n_chunks, axis=-2),  # pylint: disable=no-value-for-parameter
      ]),
      Map([
          # TODO(kitaev): Test whether dropout should go before or after the
          # LayerNorm, and whether dropout broadcasting is needed here.
          tl.LayerNorm(),
          BroadcastedDropout(rate=dropout, mode=mode),  # pylint: disable=no-value-for-parameter
          tl.Dense(vocab_size),
          tl.LogSoftmax(),
      ], n_sections=n_chunks),
  )
