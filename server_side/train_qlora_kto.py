"""AionGenos Student QLoRA — KTO (Kahneman-Tversky Optimization) refinement.

Adapts ``train_qlora_gemma4.py`` to use KTO loss instead of vanilla SFT:
  - sample-level binary label (desirable | undesirable) read from the JSONL
    field ``kto_label`` produced by prep_training_data.py with --include_failures
    --only_progress_round.
  - desirable / undesirable losses are weighted independently to compensate
    for the natural class imbalance in collect data
    (Phase 4 D6: 158 desirable vs 548 undesirable).

Reference policy:
  - Default: base 4-bit Gemma-4 with the LoRA adapter disabled.
  - With --frozen-adapter (C.3-B composable mode): base + frozen SFT adapter,
    KTO trains a SECOND LoRA on top. π_ref = π_SFT, π_θ = π_SFT + π_KTO.

KTO ref:
    Ethayarajh et al. 2024, "Model Alignment as Prospect Theoretic Optimization"
    arxiv.org/abs/2402.01306

Three modes (Phase 4 D11 C.3-B is the third):

1. KTO from base (fast iteration):
    python3 train_qlora_kto.py \\
        --jsonl-path data/training_sets/v33_d6_optC_plus.jsonl \\
        --output-dir checkpoints/v4_kto/

2. Single-adapter SFT→KTO (C.1, sequential same-adapter):
    python3 train_qlora_gemma4.py --jsonl-path ... --output-dir checkpoints/v4_sft/
    python3 train_qlora_kto.py --warm-start checkpoints/v4_sft/final_adapter \\
            --jsonl-path ... --output-dir checkpoints/v4_kto/

3. Composable dual-adapter (C.3-B, Phase 4 D11 chosen approach):
    python3 train_qlora_gemma4.py --jsonl-path <sft.jsonl> \\
            --output-dir checkpoints/v4_sft_A/
    python3 train_qlora_kto.py --frozen-adapter checkpoints/v4_sft_A/final_adapter \\
            --jsonl-path <kto.jsonl> \\
            --output-dir checkpoints/v4_kto_B/
    Deploy:  llama-server --lora v4_sft_A.gguf --lora v4_kto_B.gguf
"""

import argparse
import json
import os
import sys
from pathlib import Path
from PIL import Image

import torch
import torch.nn as nn
import torch.nn.functional as F
import torchvision
from torch.utils.data import Dataset

# ==================== System/Venv Compatibility Patches ====================
original_path = list(sys.path)
sys.path.insert(0, "/home/exx/CYTu/test_zone/gemma3-bbox-finetune/.venv/lib/python3.10/site-packages")

try:
    import torch.nn.attention.flex_attention as fa
    fa.AuxRequest = type('AuxRequest', (object,), {})
except Exception:
    pass

torch.float8_e8m0fnu = getattr(torch, "float8_e8m0fnu", torch.uint8)

# ==================== Monkey-Patch PEFT #3129 for Gemma 4 ====================
try:
    from transformers.models.gemma4 import modeling_gemma4

    class PatchedClippableLinear(nn.Linear):
        def __init__(self, config, in_features, out_features):
            nn.Linear.__init__(self, in_features, out_features, bias=False)
            self.use_clipped_linears = getattr(config, "use_clipped_linears", False)
            if self.use_clipped_linears:
                self.register_buffer("input_min", torch.tensor(-float("inf")))
                self.register_buffer("input_max", torch.tensor(float("inf")))
                self.register_buffer("output_min", torch.tensor(-float("inf")))
                self.register_buffer("output_max", torch.tensor(float("inf")))

        def forward(self, x):
            if self.use_clipped_linears:
                x = torch.clamp(x, self.input_min, self.input_max)
            out = nn.Linear.forward(self, x)
            if self.use_clipped_linears:
                out = torch.clamp(out, self.output_min, self.output_max)
            return out

    modeling_gemma4.Gemma4ClippableLinear = PatchedClippableLinear
    print("Successfully monkey-patched Gemma4ClippableLinear for PEFT compatibility.")
except Exception as e:
    print(f"Warning: Could not monkey-patch Gemma4ClippableLinear: {e}")

from transformers import (
    AutoProcessor,
    AutoModelForMultimodalLM,
    BitsAndBytesConfig,
    TrainingArguments,
    Trainer,
)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training, PeftModel

sys.path = original_path

STAGE1_SYSTEM = (
    "You are a bimanual robot controller. You receive a camera image of the scene "
    "and must plan the next sub-goal for both arms.\n"
    "Rules:\n- All coordinates are integers in [-100, 100].\n"
    "- Never output floating point numbers for coordinates.\n"
    "- Reason step-by-step about the physics before giving targets.\n"
    "- Output your response in the EXACT format specified below."
)


# ─────────────────────────────────────────────────────────────────────────
# Dataset — same format as JsonlReplayDataset but exposes `is_desirable`.
# ─────────────────────────────────────────────────────────────────────────


class KtoJsonlDataset(Dataset):
    """One sample per JSONL line, carrying the kto_label as a boolean.

    Lines without a kto_label are skipped — KTO loss is undefined for those.
    Use prep_training_data.py with --include_failures --only_progress_round
    to produce a JSONL where every row has kto_label set.
    """

    def __init__(self, jsonl_path, processor, max_length=2048):
        self.processor = processor
        self.max_length = max_length
        self.examples = []

        n_desirable = n_undesirable = n_skipped = 0
        print(f"Loading KTO dataset from JSONL: {jsonl_path}")
        with open(jsonl_path, "r") as fp:
            for line_no, raw in enumerate(fp, 1):
                line = raw.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError as e:
                    print(f"  line {line_no}: bad JSON, skip ({e})")
                    continue

                label = rec.get("kto_label")
                if label not in ("desirable", "undesirable"):
                    n_skipped += 1
                    continue

                img_path = Path(rec["image_path"])
                if not img_path.exists():
                    print(f"  line {line_no}: missing image {img_path}, skip")
                    n_skipped += 1
                    continue
                image = Image.open(img_path).convert("RGB")

                state = rec.get("state", {}) or {}
                left_pos = state.get("left_ee", [0, 0, 0])
                right_pos = state.get("right_ee", [0, 0, 0])
                instruction = rec.get("task_instruction", "")
                user_content = (
                    f"TASK: {instruction}\n"
                    f"CONTROL_MODE: end_effector_position_only\n\n"
                    f"CURRENT STATE:\n"
                    f"  LEFT_EE_POS  = (X={left_pos[0]}, Y={left_pos[1]}, Z={left_pos[2]})\n"
                    f"  RIGHT_EE_POS = (X={right_pos[0]}, Y={right_pos[1]}, Z={right_pos[2]})\n\n"
                    f"THOUGHT: <one paragraph physics reasoning>\n"
                    f"LEFT_TARGET_POS:  X=<int> Y=<int> Z=<int>\n"
                    f"RIGHT_TARGET_POS: X=<int> Y=<int> Z=<int>\n"
                    f"STOP: <true|false>"
                )
                critic = rec.get("critic_feedback")
                if critic:
                    user_content += f"\n\n### CRITIC FEEDBACK FROM PREVIOUS ROUND:\n{critic}"

                response_text = rec.get("target_response", "")
                if not response_text.strip():
                    n_skipped += 1
                    continue

                self.examples.append({
                    "image": image,
                    "system_prompt": STAGE1_SYSTEM,
                    "user_prompt": user_content,
                    "response": response_text,
                    "is_desirable": (label == "desirable"),
                })
                if label == "desirable":
                    n_desirable += 1
                else:
                    n_undesirable += 1

        print(f"  loaded: {n_desirable} desirable + {n_undesirable} undesirable "
              f"({len(self.examples)} total, {n_skipped} skipped)")

    def __len__(self):
        return len(self.examples)

    def __getitem__(self, idx):
        ex = self.examples[idx]
        image = ex["image"]

        full_prompt = (
            f"<start_of_turn>user\n{ex['system_prompt']}\n<|image|>\n{ex['user_prompt']}<end_of_turn>\n"
            f"<start_of_turn>model\n"
        )
        full_text = f"{full_prompt}{ex['response']}<end_of_turn>"
        batch = self.processor(text=full_text, images=image, return_tensors="pt")

        input_ids = batch["input_ids"][0]
        attention_mask = batch["attention_mask"][0]
        pixel_values = batch["pixel_values"][0] if "pixel_values" in batch else None
        image_position_ids = batch["image_position_ids"][0] if "image_position_ids" in batch else None
        mm_token_type_ids = batch["mm_token_type_ids"][0] if "mm_token_type_ids" in batch else None

        labels = input_ids.clone()
        prompt_batch = self.processor(text=full_prompt, images=image, return_tensors="pt")
        prompt_len = prompt_batch["input_ids"].shape[1]
        labels[:prompt_len] = -100  # only response tokens contribute to loss

        # Manual truncation
        if len(input_ids) > self.max_length:
            input_ids = input_ids[:self.max_length]
            attention_mask = attention_mask[:self.max_length]
            labels = labels[:self.max_length]
            if image_position_ids is not None:
                image_position_ids = image_position_ids[:self.max_length]
            if mm_token_type_ids is not None:
                mm_token_type_ids = mm_token_type_ids[:self.max_length]

        item = {
            "input_ids": input_ids,
            "attention_mask": attention_mask,
            "labels": labels,
            "is_desirable": torch.tensor(ex["is_desirable"], dtype=torch.bool),
        }
        if pixel_values is not None:
            item["pixel_values"] = pixel_values
        if image_position_ids is not None:
            item["image_position_ids"] = image_position_ids
        if mm_token_type_ids is not None:
            item["mm_token_type_ids"] = mm_token_type_ids
        return item


def collate_fn(batch):
    input_ids = [item["input_ids"] for item in batch]
    attention_mask = [item["attention_mask"] for item in batch]
    labels = [item["labels"] for item in batch]
    is_desirable = torch.stack([item["is_desirable"] for item in batch])

    input_ids = torch.nn.utils.rnn.pad_sequence(input_ids, batch_first=True, padding_value=0)
    attention_mask = torch.nn.utils.rnn.pad_sequence(attention_mask, batch_first=True, padding_value=0)
    labels = torch.nn.utils.rnn.pad_sequence(labels, batch_first=True, padding_value=-100)

    collated = {
        "input_ids": input_ids,
        "attention_mask": attention_mask,
        "labels": labels,
        "is_desirable": is_desirable,
    }

    if "pixel_values" in batch[0]:
        collated["pixel_values"] = torch.stack([item["pixel_values"] for item in batch])
    if "image_position_ids" in batch[0]:
        ip = [item["image_position_ids"] for item in batch]
        collated["image_position_ids"] = torch.nn.utils.rnn.pad_sequence(ip, batch_first=True, padding_value=-1)
    if "mm_token_type_ids" in batch[0]:
        mt = [item["mm_token_type_ids"] for item in batch]
        collated["mm_token_type_ids"] = torch.nn.utils.rnn.pad_sequence(mt, batch_first=True, padding_value=0)
    return collated


# ─────────────────────────────────────────────────────────────────────────
# KTO loss — custom Trainer subclass.
# ─────────────────────────────────────────────────────────────────────────


def _response_log_probs(logits: torch.Tensor, labels: torch.Tensor) -> torch.Tensor:
    """Per-sequence sum of log p(y_t) over response tokens (labels != -100)."""
    # Shift so labels at position t correspond to logits at position t-1
    shift_logits = logits[..., :-1, :].contiguous()
    shift_labels = labels[..., 1:].contiguous()

    log_probs = F.log_softmax(shift_logits, dim=-1)
    mask = (shift_labels != -100).float()
    # gather the log-prob of the correct token
    safe_labels = shift_labels.clamp(min=0)
    token_log_probs = log_probs.gather(-1, safe_labels.unsqueeze(-1)).squeeze(-1)
    token_log_probs = token_log_probs * mask
    return token_log_probs.sum(dim=-1)  # (B,)


class KTOTrainer(Trainer):
    """Custom Trainer implementing the KTO loss.

    Loss per sample:
        v = β · (log π_θ(y|x) - log π_ref(y|x))
        L_desirable   = -λ_d · σ(v - z_0)
        L_undesirable = -λ_u · σ(z_0 - v)

    where z_0 is a running estimate of E[β · KL(π_θ || π_ref)] (we use the
    paper's recommended estimator: detach the in-batch ref-policy log-ratio
    mean across the batch and treat it as the KL proxy). λ_d and λ_u
    rebalance the (often skewed) desirable/undesirable counts.
    """

    def __init__(
        self,
        *args,
        beta: float = 0.1,
        lambda_d: float = 1.0,
        lambda_u: float = 1.0,
        ref_mode: str = "disable",   # "disable" | "frozen_only"
        trainable_adapter_name: str = "kto",
        frozen_adapter_name: str = "sft_frozen",
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.beta = beta
        self.lambda_d = lambda_d
        self.lambda_u = lambda_u
        self.ref_mode = ref_mode
        self.trainable_adapter_name = trainable_adapter_name
        self.frozen_adapter_name = frozen_adapter_name
        if ref_mode not in ("disable", "frozen_only"):
            raise ValueError(f"ref_mode must be 'disable' or 'frozen_only', got {ref_mode!r}")

    def _ref_logits(self, inputs: dict) -> torch.Tensor:
        """Reference-policy forward pass.

        Two modes:
          - "disable": drop ALL PEFT adapters — π_ref = base model.
            Used in single-adapter mode (--warm-start or from-base).
          - "frozen_only": switch active-adapter set to {frozen SFT} only —
            π_ref = base + frozen SFT adapter. Used in C.3-B composable mode.
            Requires the model to have BOTH adapters loaded (frozen + trainable);
            after ref pass we restore both to active so π_θ = base + both.
        """
        with torch.no_grad():
            if self.ref_mode == "disable":
                with self.model.disable_adapter():
                    out = self._forward_no_grad(inputs)
            else:  # "frozen_only"
                # In C.3-B mode both adapters were loaded via
                # PeftModel.load_adapter, giving them named entries.
                # For the policy pass we want [frozen + trainable] active;
                # for the ref pass we want [frozen] only.
                try:
                    # Ref pass: LoraModel switches to frozen only.
                    self.model.base_model.set_adapter(self.frozen_adapter_name)
                    out = self._forward_no_grad(inputs)
                finally:
                    # Restore both at LoraModel layer. Keep PeftModel-level
                    # active_adapter as single string ("kto") so PEFT
                    # introspection paths don't hit unhashable-list bugs.
                    self.model.base_model.set_adapter(
                        [self.frozen_adapter_name, self.trainable_adapter_name]
                    )
                    self.model.active_adapter = self.trainable_adapter_name
        return out.logits

    def _forward_no_grad(self, inputs: dict):
        """Shared forward-only helper."""
        return self.model(
            input_ids=inputs["input_ids"],
            attention_mask=inputs["attention_mask"],
            pixel_values=inputs.get("pixel_values"),
            image_position_ids=inputs.get("image_position_ids"),
            mm_token_type_ids=inputs.get("mm_token_type_ids"),
        )

    def compute_loss(self, model, inputs, return_outputs=False, num_items_in_batch=None):
        is_desirable = inputs.pop("is_desirable")
        labels = inputs["labels"]

        # Policy logits (LoRA on)
        out = model(**{k: v for k, v in inputs.items() if k != "labels"}, labels=None)
        policy_logits = out.logits

        # Reference logits (LoRA off)
        ref_logits = self._ref_logits(inputs)

        policy_logp = _response_log_probs(policy_logits, labels)      # (B,)
        with torch.no_grad():
            ref_logp = _response_log_probs(ref_logits, labels)        # (B,)

        # KL proxy: mean log-ratio over the batch, detached.
        log_ratio = policy_logp - ref_logp                              # (B,)
        v = self.beta * log_ratio                                       # (B,)
        z0 = v.detach().mean().clamp(min=0.0)                           # scalar

        sig_pos = torch.sigmoid(v - z0)
        sig_neg = torch.sigmoid(z0 - v)

        loss_per_sample = torch.where(
            is_desirable,
            -self.lambda_d * sig_pos,
            -self.lambda_u * sig_neg,
        )

        loss = loss_per_sample.mean()

        # Helpful aux logging
        with torch.no_grad():
            self._n_steps = getattr(self, "_n_steps", 0) + 1
            if self._n_steps % 10 == 1:
                n_d = int(is_desirable.sum().item())
                n_u = int((~is_desirable).sum().item())
                print(
                    f"  step {self._n_steps:4d} | loss={loss.item():.4f} | "
                    f"v.mean={v.mean().item():+.3f} z0={z0.item():.3f} | "
                    f"d/u={n_d}/{n_u}"
                )
        return (loss, out) if return_outputs else loss


# ─────────────────────────────────────────────────────────────────────────
# Main entry — wires the model, dataset, and KTOTrainer together.
# ─────────────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(description="AionGenos Student QLoRA — KTO refinement")
    parser.add_argument("--jsonl-path", type=str, required=True,
                        help="JSONL training set with kto_label field per row.")
    parser.add_argument("--output-dir", type=str, required=True)
    parser.add_argument("--base-model", type=str, default="google/gemma-4-31b-it")
    parser.add_argument("--warm-start", type=str, default=None,
                        help="Optional path to a previously-trained LoRA adapter. "
                             "When set (single-adapter mode / C.1), the adapter is "
                             "loaded ON TOP OF the base and continues training under "
                             "KTO loss (in-place). π_ref = base with adapter disabled. "
                             "Mutually exclusive with --frozen-adapter.")
    parser.add_argument("--frozen-adapter", type=str, default=None,
                        help="Phase 4 C.3-B composable mode. Path to a previously-"
                             "trained SFT adapter. That adapter is loaded as FROZEN "
                             "with name 'sft_frozen'. A SECOND adapter named 'kto' "
                             "is added trainable. π_ref = base + sft_frozen, "
                             "π_θ = base + sft_frozen + kto. Output saves the 'kto' "
                             "adapter only. Deploy uses both at inference. Mutually "
                             "exclusive with --warm-start.")
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--lr", type=float, default=5e-5)
    parser.add_argument("--beta", type=float, default=0.1,
                        help="KTO beta — temperature on the log-ratio.")
    parser.add_argument("--lambda-d", type=float, default=1.0,
                        help="Weight on desirable loss.")
    parser.add_argument("--lambda-u", type=float, default=1.0,
                        help="Weight on undesirable loss. Tip: when desirable << "
                             "undesirable in the data, raise lambda_d to "
                             "rebalance — e.g. for 158 desirable / 548 undesirable, "
                             "lambda_d = 548/158 ≈ 3.47, lambda_u = 1.0.")
    parser.add_argument("--auto-balance", action="store_true",
                        help="Auto-compute (lambda_d, lambda_u) from class counts "
                             "(overrides --lambda-d / --lambda-u).")
    parser.add_argument("--run-tag", type=str, default=None,
                        help="Amendment 7 §7.6 / Amendment 10 §10.4 (item 6): "
                             "arm-level identifier for this run "
                             "(e.g. 'A_action_only', 'A_ctrl_rat', 'B_main', "
                             "'D_gist'). Written into training_meta.json under "
                             "output-dir alongside effective-step count and the "
                             "full hyperparam set so cross-arm equivalence is "
                             "auditable after the fact.")
    args = parser.parse_args()

    if args.warm_start and args.frozen_adapter:
        print("Error: --warm-start and --frozen-adapter are mutually exclusive.")
        sys.exit(1)

    print(f"Loading processor for base model: {args.base_model}")
    processor = AutoProcessor.from_pretrained(args.base_model)

    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True,
        bnb_4bit_compute_dtype=torch.bfloat16,
    )

    print(f"Loading base model in 4-bit: {args.base_model}")
    model = AutoModelForMultimodalLM.from_pretrained(
        args.base_model,
        quantization_config=bnb_config,
        device_map="auto",
    )

    model = prepare_model_for_kbit_training(model)

    # LoRA config used for any fresh trainable adapter.
    fresh_lora_cfg = LoraConfig(
        r=16,
        lora_alpha=32,
        target_modules=".*language_model\\.layers\\.\\d+\\.(self_attn\\.(q|k|v|o)_proj|mlp\\.(gate|up|down)_proj)",
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
    )

    ref_mode = "disable"  # default: single-adapter mode
    if args.frozen_adapter:
        # ── C.3-B composable mode ─────────────────────────────────────────
        # Load SFT adapter as frozen (adapter_name="sft_frozen"), then add
        # a fresh trainable "kto" adapter on top. π_ref = base + sft_frozen,
        # π_θ = base + sft_frozen + kto.
        print(f"C.3-B mode: loading SFT adapter as FROZEN from {args.frozen_adapter}")
        model = PeftModel.from_pretrained(
            model, args.frozen_adapter,
            adapter_name="sft_frozen", is_trainable=False,
        )
        print("Adding fresh trainable 'kto' adapter...")
        model.add_adapter("kto", fresh_lora_cfg)
        # Activate both: π_θ pass uses both, ref pass switches to sft_frozen only.
        # PEFT 0.19: PeftModel.set_adapter is single-string only. LoraModel
        # (accessed via .base_model) still supports list — that's what
        # actually turns the LoRA layers on/off. The C.3-B invariant is:
        # both adapters route through forward at the LoraModel layer level.
        # PeftModel.active_adapter (used by Trainer for introspection) stays
        # as a single string pointing to the TRAINABLE adapter; PEFT internal
        # code does `peft_config[active_adapter]` which requires hashable key.
        model.base_model.set_adapter(["sft_frozen", "kto"])
        model.active_adapter = "kto"  # single-string for PEFT introspection
        # Freeze parameters that belong to sft_frozen (paranoid — PEFT should
        # already handle this via is_trainable=False, but ensure at param level).
        n_kto_trainable = n_frozen = 0
        for name, p in model.named_parameters():
            if "lora_" in name and "sft_frozen" in name:
                p.requires_grad = False
                n_frozen += 1
            elif "lora_" in name and "kto" in name:
                p.requires_grad = True
                n_kto_trainable += 1
        print(f"  frozen sft params: {n_frozen}  trainable kto params: {n_kto_trainable}")
        assert n_kto_trainable > 0, "no trainable KTO adapter params — check target_modules"
        ref_mode = "frozen_only"
    elif args.warm_start:
        # ── C.1 single-adapter mode (in-place continue-training) ──────────
        print(f"Warm-starting from SFT adapter: {args.warm_start}")
        model = PeftModel.from_pretrained(model, args.warm_start, is_trainable=True)
    else:
        # ── KTO-from-base mode ────────────────────────────────────────────
        print("Creating fresh PEFT model wrapper (KTO from base, no warm-start)...")
        model = get_peft_model(model, fresh_lora_cfg)

    model.print_trainable_parameters()

    dataset = KtoJsonlDataset(args.jsonl_path, processor)
    if len(dataset) == 0:
        print("Error: No valid KTO training examples loaded. Exiting.")
        sys.exit(1)

    if args.auto_balance:
        n_d = sum(1 for ex in dataset.examples if ex["is_desirable"])
        n_u = len(dataset) - n_d
        if n_d == 0 or n_u == 0:
            print(f"WARN: cannot auto-balance (n_d={n_d}, n_u={n_u}), using lambda=1/1")
            args.lambda_d = args.lambda_u = 1.0
        else:
            args.lambda_d = max(n_d, n_u) / n_d
            args.lambda_u = max(n_d, n_u) / n_u
            print(f"  auto-balance: lambda_d={args.lambda_d:.3f}, lambda_u={args.lambda_u:.3f}")

    training_args = TrainingArguments(
        output_dir=args.output_dir,
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        gradient_accumulation_steps=4,
        warmup_ratio=0.03,
        learning_rate=args.lr,
        logging_steps=1,
        save_strategy="epoch",
        eval_strategy="no",
        fp16=False,
        bf16=True,
        optim="paged_adamw_8bit",
        remove_unused_columns=False,
    )

    trainer = KTOTrainer(
        model=model,
        args=training_args,
        train_dataset=dataset,
        data_collator=collate_fn,
        beta=args.beta,
        lambda_d=args.lambda_d,
        lambda_u=args.lambda_u,
        ref_mode=ref_mode,
    )

    # Amendment 7 §7.6 / Amendment 10 §10.4 (item 6): compute + record the
    # effective step count so all 2×2 arms can be shown to have received
    # identical optimizer exposure.
    n_samples = len(dataset)
    ga = training_args.gradient_accumulation_steps
    bs = training_args.per_device_train_batch_size
    world = max(1, int(os.environ.get("WORLD_SIZE", 1)))
    effective_batch = bs * ga * world
    steps_per_epoch = max(1, n_samples // effective_batch)
    effective_steps = steps_per_epoch * int(args.epochs)

    training_meta = {
        "run_tag": args.run_tag,
        "jsonl_path": args.jsonl_path,
        "n_samples": n_samples,
        "epochs": int(args.epochs),
        "per_device_batch_size": bs,
        "gradient_accumulation_steps": ga,
        "world_size": world,
        "effective_batch": effective_batch,
        "steps_per_epoch": steps_per_epoch,
        "effective_steps": effective_steps,
        "lr": args.lr,
        "warmup_ratio": training_args.warmup_ratio,
        "beta": args.beta,
        "lambda_d": args.lambda_d,
        "lambda_u": args.lambda_u,
        "auto_balance": args.auto_balance,
        "ref_mode": ref_mode,
        "frozen_adapter": args.frozen_adapter,
        "warm_start": args.warm_start,
        "base_model": args.base_model,
    }
    os.makedirs(args.output_dir, exist_ok=True)
    meta_path = os.path.join(args.output_dir, "training_meta.json")
    with open(meta_path, "w") as fp:
        json.dump(training_meta, fp, indent=2)
    print(f"Wrote training meta → {meta_path}")
    print(
        f"Effective steps: {effective_steps} "
        f"(n={n_samples}, bs={bs}, ga={ga}, world={world}, epochs={args.epochs})"
    )

    print(
        f"Starting KTO fine-tuning... "
        f"beta={args.beta} lambda_d={args.lambda_d:.3f} lambda_u={args.lambda_u:.3f}"
    )
    trainer.train()

    final_output_path = os.path.join(args.output_dir, "final_adapter")
    print(f"Saving final LoRA adapter(s) to {final_output_path}")
    if ref_mode == "frozen_only":
        # C.3-B: save ONLY the trainable kto adapter. The frozen sft_frozen
        # adapter should be re-loaded from its original path at inference time
        # via llama-server --lora, not duplicated here.
        trainer.model.save_pretrained(final_output_path, selected_adapters=["kto"])
        print(f"  saved adapter: kto")
        print(f"  frozen sft adapter left at its input path: {args.frozen_adapter}")
        print(f"  inference: base + {args.frozen_adapter}/*.gguf + {final_output_path}/*.gguf (both --lora)")
    else:
        # C.1 / from-base: single default adapter.
        trainer.model.save_pretrained(final_output_path)
    print("KTO training complete!")


if __name__ == "__main__":
    main()
