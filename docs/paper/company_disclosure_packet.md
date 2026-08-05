# Disclosure & Publication-Permission Request — personal research using company resources

**Author:** Cheng-Yin Tu
**To:** [manager / NRCA IP or legal contact — AUTHOR: fill]
**Date:** 2026-08-04 (draft v2 — reframed)
**Purpose:** This is a **proactive disclosure and request for permission
to publish** externally. The research was carried out **using NRCA
(Nikon Research Corporation of America) hardware, partly during working
hours**. I am disclosing it in full and asking (1) permission to publish,
(2) clarification of IP / authorship attribution, and (3) any required
affiliation / acknowledgement wording. Three parts: (1) non-confidential
content summary, (2) disclosure list (venues, nature, public timing),
(3) resource & working-arrangement statement.

> **DRAFT — author to review before sending.** Fields marked `[AUTHOR:
> …]` need the author's input or a company answer and must be resolved
> before this goes to the company. Affiliation is intentionally left open
> — it is one of the things this request asks the company to decide.

---

## Part 1 — Non-confidential content summary (~1 page)

**Field.** General-purpose machine-learning methodology research on
*memory architecture* for embodied learning agents — whether an agent's
accumulated experience should be stored in model weights (parametric) or
kept external and retrieved at inference (contextual). The work uses only
public open-weight models, a public open-source robotics simulator, and
synthetic data generated in simulation.

**Relationship to company business.** To the best of my knowledge the
topic is general ML methodology and does **not** touch any Nikon/NRCA
product, business line, customer data, optical/imaging technology, or
proprietary method. I flag this for the company's own assessment rather
than asserting it as settled — that assessment is part of what I am
requesting.

**Question studied.** When an embodied agent accumulates experience,
should that experience be baked into its policy weights, or kept external
and retrieved when needed?

**Method (public tools only).** A memory-augmented teacher model produces
trajectories on a simulated robotic reaching task; student policies are
distilled from those trajectories and evaluated under matched protocols,
including one that supplies the same memory via retrieval at inference
instead of via training. All models are public open-weight VLMs; the
simulator is public; all data is synthetic.

**Headline finding.** Distilling memory into weights recovered
essentially none of the memory benefit, while attaching the *same* memory
as an inference-time retrieval context recovered it in full — a design
principle ("distil the competence, externalise the memory") plus a
mechanistic account of why. A second, harder task shows the same
direction at reduced, non-significant magnitude. The methodological
emphasis is pre-registration: hypotheses and analysis rules were fixed
before results.

---

## Part 2 — Disclosure list (venues, nature, public timing)

| Venue | Nature | Peer-reviewed? | Archival? | Public at | Anonymity |
|---|---|---|---|---|---|
| **arXiv** | Preprint server | No | N/A (preprint) | Immediately on upload | Non-anonymous (author named) |
| **TMLR** (Transactions on Machine Learning Research) | Journal, via OpenReview | Yes | Archival | On acceptance / camera-ready | Non-anonymous |
| **BAR @ NeurIPS 2026** (workshop) | Workshop paper (4 pp) | Light review | **Non-archival** (official NeurIPS workshop policy) | On workshop acceptance / event (Sydney, 2026-12-11) | **Double-blind** submission |

**Timing notes:**
- **Nothing is submitted before the company clears this request.** arXiv
  and TMLR are held pending clearance; TMLR's timeline is therefore
  company-review-gated and not under my control.
- **BAR has a hard external deadline of 2026-08-29 (AoE)** that cannot be
  moved. The 4-page workshop paper is prepared so it can be submitted the
  moment clearance lands; it will **not** be submitted before clearance.
  If clearance cannot be completed before 2026-08-29, the BAR submission
  is simply forgone — I am not asking the deadline to override review.
- **Non-archival** status of BAR means it is not a formal publication of
  record and does not conflict with the TMLR journal version (standard
  workshop-for-feedback / journal-for-record dual track).
- `[AUTHOR / COMPANY: confirm]` any required review lead-time; I will
  respect whatever window the company sets.

---

## Part 3 — Resource & working-arrangement statement (full, honest disclosure)

Stated plainly for the company's assessment:

- **Hardware.** Training and evaluation used **NRCA hardware**:
  - a local workstation with a single **NVIDIA RTX A4500** (simulation,
    data collection, LIBERO/robosuite work), and
  - a remote **3-GPU workstation** (135 GB VRAM total; the teacher/student
    inference servers and the LoRA training runs — `CUDA_VISIBLE_DEVICES=1,2`
    for training, GPU 0 for inference).
  `[AUTHOR: confirm the exact machine names/asset tags if the company
  wants them.]`
- **Working time.** The work was done **partly during working hours and
  partly on personal time.** I am not representing it as done exclusively
  off-hours. `[AUTHOR: add any detail the company expects, e.g. approx.
  split or whether a manager was aware.]`
- **Data.** No Nikon/NRCA data of any kind was used. All data is synthetic,
  generated in a public open-source robotics simulator; the models are
  public open-weight releases.
- **IP / confidential information.** The work uses no company trade
  secrets, product information, or confidential material, and (to my
  knowledge) does not touch the company's business domain — but **because
  company hardware and partial working time were used, I am not asserting
  the IP position; I am asking the company to determine it** (ownership,
  license-back, or release), and I will follow that determination.
- **Software / accounts.** `[AUTHOR: confirm]` whether any company
  software licenses or accounts were used beyond the hardware above.

---

## Part 4 — What I am requesting from the company

1. **Permission to publish** the non-confidential content in Part 1 at the
   venues in Part 2.
2. **IP / authorship determination** — given company hardware + partial
   working time, please advise ownership and whether/how I may publish
   (e.g. as company-affiliated work, or released as personal work).
3. **Affiliation & acknowledgement wording** — whether the paper should
   list **Nikon Research Corporation of America** as the affiliation
   and/or carry a specific acknowledgement. *(The paper's affiliation line
   is deliberately unset pending this answer.)*
4. **Any review window** I must observe before the earliest public date.

---

## Notes for the author (not part of the packet)
- Affiliation decision is downstream of this request — do NOT set it on
  the arXiv/TMLR manuscript until the company answers (main.tex currently
  carries an "affiliation TBD" placeholder + personal email, which is the
  right holding state).
- The framing changed from v1 ("independent personal work") to v2
  ("company-resource disclosure + permission request") after the author
  clarified: NRCA hardware, partial working hours. v1's independent
  framing would have mis-stated the facts to the employer — v2 is the
  honest and safe framing.
- Fact base for Part 3 verified against repo (2026-08-04):
  run_d11_pipeline.sh uses `CUDA_VISIBLE_DEVICES=1,2` (remote training on
  2 of 3 GPUs); llama_server_*.sh deploy on the remote 135 GB-VRAM host;
  l2_stage1_pipeline.sh references the "LOCAL A4500". Both machines = NRCA.
