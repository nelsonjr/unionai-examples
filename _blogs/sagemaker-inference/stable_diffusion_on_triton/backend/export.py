# Copyright (c) 2022, NVIDIA CORPORATION & AFFILIATES. All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#  * Neither the name of NVIDIA CORPORATION nor the names of its
#    contributors may be used to endorse or promote products derived
#    from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS ``AS IS'' AND ANY
# EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
# PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY
# OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import sys

import torch
from diffusers import AutoencoderKL
from transformers import CLIPTextModel, CLIPTokenizer

if len(sys.argv) > 1:
    fused_model = sys.argv[1]
    encoder_file_name = sys.argv[2]

# VAE
vae = AutoencoderKL.from_pretrained(fused_model, subfolder="vae", cache_dir="hf_cache")
vae.forward = vae.decode
torch.onnx.export(
    vae,
    (torch.randn(1, 4, 64, 64), False),
    "vae.onnx",
    input_names=["latent_sample", "return_dict"],
    output_names=["sample"],
    dynamic_axes={
        "latent_sample": {0: "batch", 1: "channels", 2: "height", 3: "width"},
    },
    do_constant_folding=True,
    opset_version=14,
)

# TEXT ENCODER
tokenizer = CLIPTokenizer.from_pretrained(
    fused_model, subfolder="tokenizer", cache_dir="hf_cache"
)
text_encoder = CLIPTextModel.from_pretrained(
    fused_model, subfolder="text_encoder", cache_dir="hf_cache"
)

prompt = "Draw a dog"
text_input = tokenizer(
    prompt,
    padding="max_length",
    max_length=tokenizer.model_max_length,
    truncation=True,
    return_tensors="pt",
)
print(
    "Here is the shape of the input -----------------------------------------------------"
)
print(text_input.input_ids.shape)

torch.onnx.export(
    text_encoder,
    (text_input.input_ids.to(torch.int32)),
    encoder_file_name,
    input_names=["input_ids"],
    output_names=["last_hidden_state", "pooler_output"],
    dynamic_axes={
        "input_ids": {0: "batch", 1: "sequence"},
    },
    opset_version=14,
    do_constant_folding=True,
)
