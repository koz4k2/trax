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

import functools

from trax import layers as tl


def FeedForward(d_model, d_ff, dropout, layer_idx, mode):
  """Feed-forward block with layer normalization at start."""
  return tl.Serial(
      tl.LayerNorm(),
      tl.Dense(d_ff),
      tl.Relu(),
      tl.Dropout(rate=dropout, name='ff_middle_%d' % layer_idx, mode=mode),
      tl.Dense(d_model),
      tl.Dropout(rate=dropout, name='ff_final_%d' % layer_idx, mode=mode),
  )


def EncoderBlock(d_model, d_ff, n_heads, dropout, layer_idx, mode):
  """Returns a layer sequence that implements a Transformer encoder block.

  The input to the layer sequence is a pair, (activations, mask), where the
  mask was created from the original source tokens to prevent attending to the
  padding part of the input.

  Args:
    d_model: int:  depth of embedding
    d_ff: int: depth of feed-forward layer
    n_heads: int: number of attention heads
    dropout: float: dropout rate (how much to drop out)
    layer_idx: which layer are we at (for bookkeeping)
    mode: str: 'train' or 'eval'

  Returns:
    A sequence of layers that maps an (activations, mask) pair to an
    (activations, mask) pair.
  """
  attention = [
      tl.LayerNorm(),
      tl.Attention(d_model, n_heads=n_heads, dropout=dropout, mode=mode),
      tl.Dropout(rate=dropout, name='enc_attn_dropout', mode=mode),
  ]
  feed_forward = [
      FeedForward(d_model, d_ff, dropout, layer_idx=layer_idx, mode=mode),
  ]
  return tl.Serial(
      tl.Residual(attention),
      tl.Residual(feed_forward),
  )


def TransformerEncoder(vocab_size,
                       n_classes=10,
                       d_model=512,
                       d_ff=2048,
                       n_layers=6,
                       n_heads=8,
                       dropout=0.1,
                       max_len=2048,
                       mode='train'):
  """Returns a Transformer encoder model.

  The input to the model is a tensor of tokens.

  Args:
    vocab_size: int: vocab size
    n_classes: how many classes on output
    d_model: int:  depth of embedding
    d_ff: int: depth of feed-forward layer
    n_layers: int: number of encoder/decoder layers
    n_heads: int: number of attention heads
    dropout: float: dropout rate (how much to drop out)
    max_len: int: maximum symbol length for positional encoding
    mode: str: 'train' or 'eval'

  Returns:
    A Transformer model as a layer that maps from a tensor of tokens to
    activations over a set of output classes.
  """
  embedder = [
      tl.Embedding(d_model, vocab_size),
      tl.Dropout(rate=dropout, name='emb_dropout', mode=mode),
      tl.PositionalEncoding(max_len=max_len),
  ]
  return tl.Serial(                             #      tokens
      tl.Dup(),                                 # toks toks
      tl.Parallel(embedder, tl.PaddingMask()),  # vecs mask
      [EncoderBlock(d_model, d_ff, n_heads, dropout, i, mode)
       for i in range(n_layers)],               # vecs mask
      tl.Parallel([], tl.Drop()),               # ____  0
      tl.LayerNorm(),                           # vecs
      tl.Mean(axis=1),  # Average on length.    # vecs
      tl.Dense(n_classes),                      # vecs
      tl.LogSoftmax(),                          # vecs
  )


def DecoderBlock(d_model, d_ff, n_heads, d_attention_key, d_attention_value,
                 attention_type, dropout, share_qk, layer_idx, mode):
  """Returns a layer sequence that implements a Transformer decoder block.

  The input to the layer sequence is an activation tensor.

  Args:
    d_model: int:  depth of embedding
    d_ff: int: depth of feed-forward layer
    n_heads: int: number of attention heads
    d_attention_key: int: depth of key vector for each attention head
    d_attention_value: int: depth of value vector for each attention head
    attention_type: subclass of tl.BaseCausalAttention: attention class to use
    dropout: float: dropout rate (how much to drop out)
    share_qk: bool, whether to share queries and keys
    layer_idx: which layer are we at (for bookkeeping)
    mode: str: 'train' or 'eval'

  Returns:
    A sequence of layers that maps an activation tensor to an activation tensor.
  """
  self_attention = [
      tl.LayerNorm(),  # vec
      tl.CausalAttention(
          d_model, n_heads=n_heads, d_attention_key=d_attention_key,
          d_attention_value=d_attention_value, attention_type=attention_type,
          share_qk=share_qk, mode=mode),
      tl.Dropout(rate=dropout, name='attention_%d' % layer_idx, mode=mode),
  ]
  feed_forward = [
      FeedForward(d_model, d_ff, dropout, layer_idx=layer_idx, mode=mode),
  ]
  return tl.Serial(
      tl.Residual(self_attention),
      tl.Residual(feed_forward),
  )


def TransformerDecoder(vocab_size=None,
                       d_model=512,
                       d_ff=2048,
                       n_layers=6,
                       n_heads=8,
                       d_attention_key=None,
                       d_attention_value=None,
                       attention_type=tl.DotProductCausalAttention,
                       dropout=0.1,
                       share_qk=False,
                       max_len=2048,
                       mode='train'):
  """Returns a Transformer decoder model.

  The input to the model is either continuous or discrete - controlled by
  vocab_size. Does not shift the input to the right, i.e. the output for
  timestep t is based on inputs up to timestep t inclusively.

  Args:
    vocab_size: int or None: vocab size if running on discrete input, None
        otherwise.
    d_model: int:  depth of embedding
    d_ff: int: depth of feed-forward layer
    n_layers: int: number of encoder/decoder layers
    n_heads: int: number of attention heads
    d_attention_key: int: depth of key vector for each attention head
        (default is d_model // n_heads)
    d_attention_value: int: depth of value vector for each attention head
        (default is d_model // n_heads)
    attention_type: subclass of tl.BaseCausalAttention: attention class to use
    dropout: float: dropout rate (how much to drop out)
    share_qk: bool, whether to share queries and keys in decoder attention
    max_len: int: maximum symbol length for positional encoding
    mode: str: 'train' or 'eval'

  Returns:
    A Transformer decoder as a layer that maps from a continuous or discrete
    tensor to a continuous tensor.
  """
  if vocab_size is None:
    input_layer = tl.Dense
  else:
    input_layer = functools.partial(tl.Embedding, vocab_size=vocab_size)
  return tl.Serial(                  # vecs
      input_layer(d_model),         # vecs
      tl.Dropout(rate=dropout, mode=mode),
      tl.PositionalEncoding(max_len=max_len),
      [DecoderBlock(  # pylint: disable=g-complex-comprehension
          d_model, d_ff, n_heads, d_attention_key, d_attention_value,
          attention_type, dropout, share_qk, i, mode)
       for i in range(n_layers)],   # vecs
      tl.LayerNorm(),               # vecs
  )


def TransformerLM(vocab_size,
                  d_model=512,
                  d_ff=2048,
                  n_layers=6,
                  n_heads=8,
                  d_attention_key=None,
                  d_attention_value=None,
                  attention_type=tl.DotProductCausalAttention,
                  dropout=0.1,
                  share_qk=False,
                  max_len=2048,
                  n_chunks=0,
                  mode='train'):
  """Returns a Transformer language model.

  The input to the model is a tensor of tokens. (This model uses only the
  decoder part of the overall Transformer.)

  Args:
    vocab_size: int: vocab size
    d_model: int:  depth of embedding
    d_ff: int: depth of feed-forward layer
    n_layers: int: number of encoder/decoder layers
    n_heads: int: number of attention heads
    d_attention_key: int: depth of key vector for each attention head
        (default is d_model // n_heads)
    d_attention_value: int: depth of value vector for each attention head
        (default is d_model // n_heads)
    attention_type: subclass of tl.BaseCausalAttention: attention class to use
    dropout: float: dropout rate (how much to drop out)
    share_qk: bool, whether to share queries and keys in decoder attention
    max_len: int: maximum symbol length for positional encoding
    n_chunks: int: number of chunks (must match input pipeline)
    mode: str: 'train', 'eval' or 'predict', predict mode is for fast inference

  Returns:
    A Transformer language model as a layer that maps from a tensor of tokens
    to activations over a vocab set.
  """
  if n_chunks == 0:
    concatenate_chunks = split_chunks = []
  else:
    concatenate_chunks = tl.Concatenate(n_items=n_chunks)
    split_chunks = tl.Split(n_sections=n_chunks, axis=-2)

  embedder = [
      tl.Embedding(d_model, vocab_size),
      tl.Dropout(rate=dropout, name='embedding', mode=mode),
      tl.PositionalEncoding(max_len=max_len, mode=mode),
  ]

  return tl.Serial(                  # tokens (or chunked tuple of tokens)
      concatenate_chunks,           # tokens
      tl.ShiftRight(mode=mode),     # toks
      embedder,                     # vecs
      [DecoderBlock(  # pylint: disable=g-complex-comprehension
          d_model, d_ff, n_heads, d_attention_key, d_attention_value,
          attention_type, dropout, share_qk, i, mode)
       for i in range(n_layers)],   # vecs
      tl.LayerNorm(),               # vecs
      tl.Dense(vocab_size),         # vecs
      tl.LogSoftmax(),              # vecs
      split_chunks,                 # vecs (or chunked tuple of vecs)
  )


def EncoderDecoder(d_model, d_ff, n_heads, dropout, layer_idx, mode):
  """Transformer encoder-decoder layer.

  The input is a triple (decoder_input, mask, encoder) where the mask is
  created from the original source to prevent attending to the padding part
  of the encoder.

  Args:
    d_model: int:  depth of embedding
    d_ff: int: depth of feed-forward layer
    n_heads: int: number of attention heads
    dropout: float: dropout rate (how much to drop out)
    layer_idx: which layer are we at (for bookkeeping)
    mode: str: 'train' or 'eval'

  Returns:
    the layer, returning a triple (decoder_activations, mask, encoder).
  """
  decoder_self_attention = [                    #        vecs_d   pmask vecs_e
      tl.LayerNorm(),                           #        vecs_d   ..... ......
      tl.BasicCausalAttention(
          d_model, n_heads=n_heads, dropout=dropout, mode=mode),
      tl.Dropout(rate=dropout, mode=mode),      # vecs_d          ..... ......
  ]
  decoder_to_encoder_attention = [        # vecs_d        masks         vecs_e
      tl.LayerNorm(),                     # vecs_d        masks         vecs_e
      tl.Parallel([], [], tl.Dup()),      # ______        _____  vecs_e vecs_e
      tl.Parallel([], tl.Swap()),         # ______        vecs_e masks  ......
      tl.Parallel([], tl.Dup()),          # ______ vecs_e vecs_e .....  ......
      tl.AttentionQKV(  # (q k v masks ... --> vecs_d masks ...)
          d_model, n_heads=n_heads, dropout=dropout, mode=mode),
      tl.Dropout(rate=dropout, mode=mode),  # vecs_d mask vecs_e
  ]
  feed_forward = [
      FeedForward(d_model, d_ff, dropout, layer_idx=layer_idx, mode=mode),
  ]
  return tl.Serial(                               # vecs_d masks vecs_e
      tl.Residual(decoder_self_attention),        # vecs_d masks vecs_e
      tl.Residual(decoder_to_encoder_attention),  # vecs_d masks vecs_e
      tl.Residual(feed_forward),                  # vecs_d masks vecs_e
  )


def Transformer(input_vocab_size,
                output_vocab_size=None,
                d_model=512,
                d_ff=2048,
                n_encoder_layers=6,
                n_decoder_layers=6,
                n_heads=8,
                dropout=0.1,
                max_len=2048,
                mode='train'):
  """Returns a Transformer model.

  This model expects an input pair: target, source.

  Args:
    input_vocab_size: int: vocab size of the source.
    output_vocab_size: int (optional): vocab size of the target. If None, the
      source and target are assumed to have the same vocab.
    d_model: int:  depth of embedding
    d_ff: int: depth of feed-forward layer
    n_encoder_layers: int: number of encoder layers
    n_decoder_layers: int: number of decoder layers
    n_heads: int: number of attention heads
    dropout: float: dropout rate (how much to drop out)
    max_len: int: maximum symbol length for positional encoding
    mode: str: 'train' or 'eval'

  Returns:
    A Transformer model as a layer that maps from a target, source pair to
    activations over a vocab set.
  """
  in_embed = [                                    # tokens
      tl.Embedding(d_model, input_vocab_size),  # vecs
      tl.Dropout(rate=dropout, mode=mode),        # vecs
      tl.PositionalEncoding(max_len=max_len),     # vecs
  ]

  if output_vocab_size is None:
    output_vocab_size = input_vocab_size
    out_embed = in_embed
  else:
    out_embed = [                                    # tokens
        tl.Embedding(d_model, output_vocab_size),  # vecs
        tl.Dropout(rate=dropout, mode=mode),         # vecs
        tl.PositionalEncoding(max_len=max_len),      # vecs
    ]

  encoder_stack = (  # masks vectors --> masks vectors
      [EncoderBlock(d_model, d_ff, n_heads, dropout, i, mode)
       for i in range(n_encoder_layers)])

  encoder_decoder_stack = (  # vecs_d masks vecs_e --> vecs_d masks vecs_e
      [EncoderDecoder(d_model, d_ff, n_heads, dropout, i, mode)
       for i in range(n_decoder_layers)])

  # Input: encoder_side_tokens, decoder_side_tokens
  return tl.Serial(  # tokens_e tokens_d
      tl.Parallel([], tl.Dup()),    # toks_e toks_d toks_d (for loss)
      tl.Swap(),    # toks_d toks_e ....

      # Encode.
      tl.Parallel(                                       # toks_d        toks_e
          [], [tl.Dup(),                                 # ______ toks_e toks_e
               tl.Parallel(in_embed, tl.PaddingMask()),  # ______ vecs_e masks
               encoder_stack,                            # ______ vecs_e masks
               tl.LayerNorm(),                           # ______ vecs_e .....
               tl.Swap()]),                              # ______ masks  vecs_e

      # Decode.                                  #        toks_d masks vecs_e
      tl.ShiftRight(),                           #        toks_d ..... ......
      out_embed,                                 #        vecs_d ..... ......
      tl.Dup(),                                  # vecs_d vecs_d ..... ......
      tl.Parallel([], tl.EncoderDecoderMask()),  # ______    masks     ......
      encoder_decoder_stack,                     # vecs_d    masks     vecs_e
      tl.Parallel([], tl.Drop(), tl.Drop()),     # vecs_d
      tl.LayerNorm(),                            # vecs_d
      tl.Dense(output_vocab_size),               # vecs_d
      tl.LogSoftmax(),                           # vecs_d
  )
