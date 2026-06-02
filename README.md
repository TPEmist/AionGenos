# AionGenos — Zero-Demonstration Cognitive Evolution for Embodied Intelligence

AionGenos breaks the dependency on human demonstrations (Behavior Cloning) in embodied AI.
It uses a large VLA's world model as **System 2 (slow CoT reasoning)** to generate success
trajectories in simulation with **zero demonstrations**, then distills them into **System 1
(LoRA parametric intuition)** for O(1) inference latency.

## Architecture

```
┌──────────────────────────────────┐  ┌──────────────────────────────────────┐
│ Local (RTX A4500) — Sim          │  │ Remote (135 GB VRAM) — LLM           │
│                                  │  │                                      │
│ Process A: Collector             │  │ Process B-T: Teacher (:18888)        │
│  - IsaacLab + Arena              │  │  gemma-4-31B-it multimodal           │
│  - 4-stage cognitive loop        │  │                                      │
│  - Replay buffer                 │  │ Process B-S: Student (:18889)        │
│                                  │  │  gemma-4-31B + LoRA GGUF             │
│                                  │  │                                      │
│                                  │  │ Process C: Trainer                   │
│                                  │  │  HF + peft QLoRA → GGUF export      │
└──────────────────────────────────┘  └──────────────────────────────────────┘
```

## 4-Stage Cognitive Evolution Pipeline

| Stage | Name | Description |
|-------|------|-------------|
| **1** | Reasoning | VLM sees RGB + state → CoT → integer sub-goals |
| **2** | Attempt | IK servo executes sub-goals in sim |
| **3** | Learning | On failure: critic diagnoses using observable-only data |
| **4** | Intuition | Success trajectories → QLoRA distillation → O(1) student |

## Curriculum (5 Levels)

| Lv | Task | Control |
|----|------|---------|
| L0 | Bimanual reach | Position-only (3-DoF) |
| L1 | Trajectory following | Position-only (3-DoF) |
| L2 | Push block | Position + 2-DoF RPY |
| L3 | Pick & place | Position + RPY + gripper |
| L4 | Block handover | Full bimanual coordination |

Advance rule: success rate ≥ 60% unlocks next level.

## Quick Start

```bash
# Install (local workstation)
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# M0 Smoke tests
python3 scripts/00_smoke_vlm.py      # VLM grounding sanity
bash scripts/01_smoke_isaaclab.sh     # Isaac Lab headless check
```

## Key Design Principles

1. **Zero demonstrations** — No human teleoperation data ever used
2. **Inference/training separation** — Sim and gradient updates in separate processes
3. **Scalar guard** — All coordinates as normalized integers [-100, 100], no floats for LLM
4. **Curriculum-driven** — Same codebase, same prompts across all difficulty levels
5. **Observable-only critic** — Stage 3 never uses hidden sensors

## Project Structure

```
aiongenos/
├── config.py          # Central configuration
├── vlm/               # VLM client, prompts, parser, scalar guard
├── control/           # Rotation (RPY↔quat), action modes
├── replay/            # Episode schema, buffer, sync
├── curriculum/        # Success-rate gating manager
├── pipeline/          # Stage 1-4 implementations
├── orchestrator/      # Collect loop, eval, train trigger
├── eval/              # Metrics (SR, latency, distillation gap)
└── tasks/             # IsaacLab env configs per level
```

## License

MIT
