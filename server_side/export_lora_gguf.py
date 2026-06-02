import argparse
import os
import subprocess
import sys
from pathlib import Path

def find_convert_script():
    """Search for convert_lora_to_gguf.py in common locations."""
    search_dirs = [
        Path("/data/llama.cpp"),
        Path("/root/llama.cpp"),
        Path("/home"),
        Path("."),
    ]
    
    # Check current workspace or system path first
    for d in search_dirs:
        if d.exists():
            for p in d.rglob("convert_lora_to_gguf.py"):
                if p.is_file():
                    return str(p)
                    
    # Fallback: search system PATH
    try:
        res = subprocess.run(["which", "convert_lora_to_gguf.py"], capture_output=True, text=True)
        if res.returncode == 0:
            return res.stdout.strip()
    except Exception:
        pass
        
    return None

def main():
    parser = argparse.ArgumentParser(description="Export PyTorch PEFT LoRA adapter to GGUF format")
    parser.add_argument("--checkpoint-dir", type=str, required=True, help="Directory containing LoRA checkpoint")
    parser.add_argument("--output", type=str, required=True, help="Output GGUF file path")
    parser.add_argument("--base-model", type=str, default="google/gemma-4-31b-it", help="Hugging Face base model name or path")
    args = parser.parse_args()

    # Find the convert script
    convert_script = find_convert_script()
    if not convert_script:
        print("Error: Could not locate convert_lora_to_gguf.py in llama.cpp directories.", file=sys.stderr)
        print("Please ensure llama.cpp is installed and convert_lora_to_gguf.py is available.", file=sys.stderr)
        sys.exit(1)
        
    print(f"Found llama.cpp convert script: {convert_script}")

    # The adapter weights are usually saved under a subfolder 'final_adapter' by the trainer,
    # or directly in the checkpoint directory. Let's resolve the path.
    adapter_path = Path(args.checkpoint_dir)
    if (adapter_path / "final_adapter").exists():
        adapter_path = adapter_path / "final_adapter"
        
    if not (adapter_path / "adapter_config.json").exists():
        print(f"Error: adapter_config.json not found in {adapter_path}", file=sys.stderr)
        sys.exit(1)

    # Ensure output parent directory exists
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Build llama.cpp convert command
    cmd = [
        "python3", convert_script,
        str(adapter_path),
        "--outfile", str(output_path),
        "--base", args.base_model
    ]

    print(f"Executing: {' '.join(cmd)}")
    try:
        res = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("Export completed successfully.")
        print(res.stdout)
    except subprocess.CalledProcessError as e:
        print("Error: conversion failed.", file=sys.stderr)
        print(e.stderr, file=sys.stderr)
        sys.exit(e.returncode)

if __name__ == "__main__":
    main()
