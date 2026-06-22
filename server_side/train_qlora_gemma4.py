import argparse
import glob
import json
import os
import sys
from pathlib import Path
from PIL import Image

import torch
import torch.nn as nn
import torchvision
from torch.utils.data import Dataset

# ==================== System/Venv Compatibility Patches ====================
# Restore path after imports to prevent sub-imports from pointing to wrong venv
original_path = list(sys.path)
# Prepend venv site-packages to load custom gemma-4 capable transformers/peft
sys.path.insert(0, "/home/exx/CYTu/test_zone/gemma3-bbox-finetune/.venv/lib/python3.10/site-packages")

# Apply flex_attention patch for compatibility with torch 2.6.0
try:
    import torch.nn.attention.flex_attention as fa
    fa.AuxRequest = type('AuxRequest', (object,), {})
except Exception:
    pass

# Apply float8 compatibility patch
torch.float8_e8m0fnu = getattr(torch, "float8_e8m0fnu", torch.uint8)

# ==================== Monkey-Patch PEFT #3129 for Gemma 4 ====================
# Gemma 4 uses Gemma4ClippableLinear in vision/audio towers which inherits from
# nn.Module, causing PEFT to reject target modules. We patch it to inherit from nn.Linear.
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
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training

# Restore original path to avoid side-effects on subsequent imports
sys.path = original_path

# System prompt identical to stage 1 template
STAGE1_SYSTEM = (
    "You are a bimanual robot controller. You receive a camera image of the scene "
    "and must plan the next sub-goal for both arms.\n"
    "Rules:\n- All coordinates are integers in [-100, 100].\n"
    "- Never output floating point numbers for coordinates.\n"
    "- Reason step-by-step about the physics before giving targets.\n"
    "- Output your response in the EXACT format specified below."
)


class ReplayDataset(Dataset):
    def __init__(self, json_files, processor, stage="4A", max_length=2048):
        self.processor = processor
        self.stage = stage
        self.max_length = max_length
        self.examples = []

        print(f"Loading dataset from {len(json_files)} replay files...")
        for jf in json_files:
            try:
                with open(jf, "r") as f:
                    ep_data = json.load(f)

                # Find the Stage 1 VLM interaction
                s1_interaction = None
                for interaction in ep_data.get("vlm_interactions", []):
                    if interaction.get("stage") == "stage1":  # take LAST one (the converged action)
                        s1_interaction = interaction
                        # no break: overwrite to keep the FINAL stage1 (F56 fix)

                if not s1_interaction:
                    continue

                # Locate starting RGB image (saved next to JSON file)
                episode_id = ep_data.get("episode_id")
                img_path = Path(jf).parent / f"{episode_id}_start.png"
                if not img_path.exists():
                    # Fallback to absolute/relative lookup from schema
                    fallback_path = ep_data.get("rgb_start_path")
                    if fallback_path:
                        img_path = Path(jf).parent.parent.parent.parent / fallback_path

                if not img_path.exists():
                    print(f"Warning: Image not found for {jf}, skipping.")
                    continue

                image = Image.open(img_path).convert("RGB")
                
                # Reconstruct state dict for prompt formatting
                trajectory = ep_data.get("trajectory", [])
                if not trajectory:
                    continue
                start_ts = trajectory[0]
                
                # Format system & user prompt
                instruction = ep_data.get("instruction", "")
                
                # Reconstruct prompt (L0 format helper)
                left_pos = start_ts.get("left_ee_pos", [0, 0, 0])
                right_pos = start_ts.get("right_ee_pos", [0, 0, 0])
                
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
                
                response_text = s1_interaction.get("full_response", "")
                
                self.examples.append({
                    "image": image,
                    "system_prompt": STAGE1_SYSTEM,
                    "user_prompt": user_content,
                    "response": response_text
                })
            except Exception as e:
                print(f"Error parsing {jf}: {e}")

        print(f"Successfully loaded {len(self.examples)} training examples.")

    def __len__(self):
        return len(self.examples)

    def __getitem__(self, idx):
        ex = self.examples[idx]
        image = ex["image"]
        
        # Apply standard Gemma 4 chat template format
        # Format: <start_of_turn>user\nSystem message\n<image>\nUser prompt<end_of_turn>\n<start_of_turn>model\nResponse<end_of_turn>
        full_prompt = (
            f"<start_of_turn>user\n{ex['system_prompt']}\n<|image|>\n{ex['user_prompt']}<end_of_turn>\n"
            f"<start_of_turn>model\n"
        )
        
        # 1. Tokenize full inputs (prompt + response)
        full_text = f"{full_prompt}{ex['response']}<end_of_turn>"
        batch = self.processor(text=full_text, images=image, return_tensors="pt")
        
        input_ids = batch["input_ids"][0]
        attention_mask = batch["attention_mask"][0]
        pixel_values = batch["pixel_values"][0] if "pixel_values" in batch else None
        image_position_ids = batch["image_position_ids"][0] if "image_position_ids" in batch else None
        mm_token_type_ids = batch["mm_token_type_ids"][0] if "mm_token_type_ids" in batch else None
        
        # 2. Setup labels with loss masking
        labels = input_ids.clone()
        
        # Tokenize only the prompt prefix to get prefix length
        prompt_batch = self.processor(text=full_prompt, images=image, return_tensors="pt")
        prompt_len = prompt_batch["input_ids"].shape[1]
        
        if self.stage == "4B":
            # CoT-strip refinement: mask loss on the THOUGHT section of the response
            # Split the response text to find where actions start
            response = ex["response"]
            action_start_idx = response.find("LEFT_TARGET_POS:")
            if action_start_idx == -1:
                action_start_idx = response.find("RIGHT_TARGET_POS:")
                
            if action_start_idx != -1:
                prefix_text = full_prompt + response[:action_start_idx]
                prefix_batch = self.processor(text=prefix_text, images=image, return_tensors="pt")
                prefix_len = prefix_batch["input_ids"].shape[1]
                
                # Mask up to prefix_len (System + User + THOUGHT)
                labels[:prefix_len] = -100
            else:
                # Fallback: mask only the prompt prefix
                labels[:prompt_len] = -100
        else:
            # Stage 4A: mask only the prompt prefix (keep loss on full assistant response including THOUGHT)
            labels[:prompt_len] = -100

        # Handle max length truncation manually
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
    
    # Pad sequences to max length in the batch
    input_ids = torch.nn.utils.rnn.pad_sequence(input_ids, batch_first=True, padding_value=0)
    attention_mask = torch.nn.utils.rnn.pad_sequence(attention_mask, batch_first=True, padding_value=0)
    labels = torch.nn.utils.rnn.pad_sequence(labels, batch_first=True, padding_value=-100)
    
    collated = {
        "input_ids": input_ids,
        "attention_mask": attention_mask,
        "labels": labels,
    }
    
    if "pixel_values" in batch[0]:
        collated["pixel_values"] = torch.stack([item["pixel_values"] for item in batch])
    if "image_position_ids" in batch[0]:
        image_position_ids = [item["image_position_ids"] for item in batch]
        collated["image_position_ids"] = torch.nn.utils.rnn.pad_sequence(image_position_ids, batch_first=True, padding_value=-1)
    if "mm_token_type_ids" in batch[0]:
        mm_token_type_ids = [item["mm_token_type_ids"] for item in batch]
        collated["mm_token_type_ids"] = torch.nn.utils.rnn.pad_sequence(mm_token_type_ids, batch_first=True, padding_value=0)
        
    return collated


def main():
    parser = argparse.ArgumentParser(description="AionGenos Student QLoRA Fine-tuning")
    parser.add_argument("--replay-path", type=str, required=True, help="Path to folder containing success replays")
    parser.add_argument("--output-dir", type=str, required=True, help="Checkpoint output directory")
    parser.add_argument("--base-model", type=str, default="google/gemma-4-31b-it", help="HF base model ID or path")
    parser.add_argument("--stage", type=str, default="4A", choices=["4A", "4B"], help="Distillation stage: 4A (BC with CoT) or 4B (CoT-strip)")
    parser.add_argument("--epochs", type=int, default=1, help="Number of training epochs")
    parser.add_argument("--batch-size", type=int, default=2, help="Per-device train batch size")
    parser.add_argument("--lr", type=float, default=2e-4, help="Learning rate")
    args = parser.parse_args()

    # Find JSON files
    json_files = glob.glob(os.path.join(args.replay_path, "*.json"))
    if not json_files:
        print(f"Error: No json replays found at {args.replay_path}")
        sys.exit(1)

    # 1. Initialize Processor and Model with QLoRA Configuration
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
    
    # Prepare model for kbit training
    model = prepare_model_for_kbit_training(model)
    
    # 2. LoRA Config targeting all linear layers (as per best practices for Gemma 4/VLM)
    peft_config = LoraConfig(
        r=16,
        lora_alpha=32,
        target_modules=".*language_model\\.layers\\.\\d+\\.(self_attn\\.(q|k|v|o)_proj|mlp\\.(gate|up|down)_proj)",
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
    )
    
    print("Creating PEFT model wrapper...")
    model = get_peft_model(model, peft_config)
    model.print_trainable_parameters()

    # 3. Create Dataset
    dataset = ReplayDataset(json_files, processor, stage=args.stage)
    if len(dataset) == 0:
        print("Error: No valid training examples loaded. Exiting.")
        sys.exit(1)

    # 4. Training Arguments
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

    # 5. Initialize Trainer
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=dataset,
        data_collator=collate_fn,
    )

    # 6. Run Training
    print("Starting QLoRA fine-tuning...")
    trainer.train()
    
    # Save the final adapter
    final_output_path = os.path.join(args.output_dir, "final_adapter")
    print(f"Saving final LoRA adapter to {final_output_path}")
    trainer.model.save_pretrained(final_output_path)
    print("Training complete!")


if __name__ == "__main__":
    main()
