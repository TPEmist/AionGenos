# L2/D11 GGUF conversion recipe (arch=gemma4, correct LoRA orientation)

## The bug this fixes
This llama.cpp checkout (clone a4e8912d, scripts locally edited Jun-3 2026)
has TWO defects for Gemma-4 LoRA export:

1. **No GEMMA4 arch constant.** `convert_hf_to_gguf.py` registers
   `Gemma4ForConditionalGeneration` onto `Gemma3Model` (model_arch=GEMMA3),
   so every conversion emits `general.architecture = gemma3`. The base
   model GGUF is `gemma4`, so a gemma3 adapter is rejected at load.
2. **Double-transpose.** A local working-tree edit added
   `else: lora_a, lora_b = lora_a.T, lora_b.T` in `convert_lora_to_gguf.py`
   :modify_tensors. `get_lora_A_B()` already returns llama.cpp orientation
   `[in,r]/[r,out]`; the else re-transposes back to raw PEFT `[r,in]/[out,r]`,
   which the loader rejects as "incorrect shape".

## Symptom
L2 GGUFs came out arch=gemma3, ffn_down.lora_a=[16,21504] (transposed) ->
student llama-server refused to load. D11's shipped GGUFs are gemma4,
ffn_down.lora_a=[21504,16]. Same raw safetensors, same converter -> divergence
traced to the two defects above (D11 was made before the else-transpose edit,
then arch-byte-patched).

## Recipe (reproduces D11's known-good orientation)
1. Convert with the STOCK converter (else-transpose reverted):
       /home/exx/CYTu/llama.cpp/convert_lora_STOCK.py  <adapter_dir> \
         --outfile out.gguf --base <gemma-4-31b-it snapshot>
   Run with test_zone/.venv python; it MUST live in the llama.cpp dir so
   convert_hf_to_gguf imports as a sibling module.
2. Byte-patch arch gemma3->gemma4 (equal-length, structural KV walk, asserts
   exactly one occurrence -- NOT a blind global replace):
       python3 server_side/gguf_tools/patch_arch_gemma3to4.py out.gguf

## Verification gates (all must pass)
(a) arch=gemma4 AND ffn_down.lora_a=[21504,16] (shape-identical to D11 across
    all 820 tensors -- asymmetric shapes make a value-scramble impossible).
(b) student loads on :18889, /health=200, /lora-adapters lists both.
(c) scale-1 vs scale-0 chat completion: text + per-token logprobs differ, and
    adapter text shows the trained per-arm behavior ("the left arm must move
    from its current position..."). Confirms APPLIED, not silently ignored.

## Provenance note
D11's two shipped GGUFs were retro-health-checked with gate (c) 2026-07-21 and
are mathematically live (base "coordinated grip" -> adapter "the left arm must
move"). The +34pp D11 headline rests on sound files.
