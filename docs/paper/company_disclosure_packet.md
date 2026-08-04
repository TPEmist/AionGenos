# Company Disclosure Packet — external publication of independent research

**Author:** Cheng-Yin Tu
**Date:** 2026-08-04 (draft v1)
**Purpose:** disclosure to employer ahead of external publication of
personal research, for review/clearance. Three parts: (1) non-confidential
content summary, (2) disclosure list (venues, nature, public timing),
(3) resource statement.

> **DRAFT — author to review before sending.** Fields marked `[AUTHOR:
> CONFIRM]` require the author's own attestation (only the author can
> state them) and must be verified/filled before this goes to the employer.
> Everything else is drawn from committed project artifacts.

---

## Part 1 — Non-confidential content summary (~1 page)

**Field.** General-purpose embodied-AI research on *memory architecture*
for learning agents — specifically, whether an agent's accumulated
experience should be stored in its model weights (parametric) or kept
external and retrieved at inference (contextual). The work is in the
open academic domain of machine-learning methodology and uses only
public models, public simulators, and synthetic simulation data. It has
**no relationship to any employer product, business line, customer data,
or proprietary technology** (see Part 3).

**Question studied.** When an embodied agent accumulates experience,
should that experience be baked into its policy weights, or kept external
and retrieved when needed?

**Method (public tools only).** A memory-augmented teacher model produces
trajectories on a simulated robotic reaching task; student policies are
distilled from those trajectories and evaluated under matched protocols,
including one that supplies the same memory via retrieval at inference
instead of via training. All models are public (open-weight VLMs); the
simulator is a public robotics environment; all data is synthetic,
generated in simulation.

**Headline finding.** Distilling memory into weights recovered
essentially none of the memory benefit, while attaching the *same* memory
as an inference-time retrieval context recovered it in full — leading to
a design principle ("distil the competence, externalise the memory") plus
a mechanistic account of why. A second, harder task shows the same
direction at reduced, non-significant magnitude. The study's
methodological emphasis is pre-registration: hypotheses and analysis
rules were fixed before results, so a negative result is reported as
evidence rather than buried.

**Why it is publishable and non-sensitive.** The contribution is a
general ML-methodology result about where knowledge should live in a
learning system. It contains no employer IP, no product information, no
customer or proprietary data, and no employer-specific technology. It
belongs to the same open literature as the public methods it builds on.

---

## Part 2 — Disclosure list (venues, nature, public timing)

| Venue | Nature | Peer-reviewed? | Archival? | Public at | Anonymity |
|---|---|---|---|---|---|
| **arXiv** | Preprint server | No | N/A (preprint) | Immediately on upload | Non-anonymous (author named) |
| **TMLR** (Transactions on Machine Learning Research) | Journal, via OpenReview | Yes | Archival | On acceptance / camera-ready | Non-anonymous |
| **BAR @ NeurIPS 2026** (workshop) | Workshop paper (4 pp) | Light review | **Non-archival** (official NeurIPS workshop policy) | On workshop acceptance notice / event (Sydney, 2026-12-11) | **Double-blind** submission |

**Timing notes:**
- **arXiv / TMLR are gated on this disclosure clearance** — neither is
  submitted until the employer review completes. TMLR's timeline is
  therefore not under the author's control and may be extended by review.
- **BAR has a hard external deadline of 2026-08-29 (AoE)** that cannot be
  moved. The 4-page workshop paper is being prepared so it is ready to
  submit the moment clearance lands; it will **not** be submitted before
  clearance.
- **Non-archival status of BAR** means the workshop paper is not a
  formal publication of record and does not conflict with the TMLR
  journal submission of the same work (standard dual-track: workshop for
  early feedback, journal for the archival version).
- `[AUTHOR: CONFIRM]` any employer policy on lead time between disclosure
  and publication (e.g. a mandatory N-day review window) — adjust the
  above timing so the earliest public date respects it.

---

## Part 3 — Resource statement

The following are the author's attestations. `[AUTHOR: CONFIRM]` each
line reflects the true situation before sending; edit freely — only the
author can make these statements.

- **Time.** `[AUTHOR: CONFIRM]` This research was conducted on the
  author's own personal time, outside of and unrelated to employment
  duties.
- **Hardware / compute.** `[AUTHOR: CONFIRM]` All computation ran on the
  author's own / privately-arranged hardware (a single workstation-class
  GPU). No employer computing resources, cloud accounts, or lab equipment
  were used.
- **Data.** No employer data of any kind was used. All data is synthetic,
  generated by the author in a public open-source robotics simulator; the
  models are public open-weight releases.
- **IP / confidential information.** The work uses no employer
  intellectual property, trade secrets, product information, or
  confidential material. It does not touch the employer's business domain.
- **No employer facilities or accounts.** `[AUTHOR: CONFIRM]` No employer
  networks, storage, software licenses, or accounts were used in the
  research or its writeup.

---

## Notes for the author (not part of the packet)
- Keep Part 1 free of anything that could be read as employer-domain-
  specific; the current text scopes it to generic embodied-AI/ML memory
  architecture, which it genuinely is.
- If the employer requires the actual manuscript, the arXiv PDF (once
  affiliation is decided) is the artifact to attach — it is the same
  non-confidential content, in full.
- Affiliation decision (Nikon vs independent) interacts with this packet:
  if the employer clears it as independent personal work, the paper may
  list an independent/no affiliation; if filed under the employer, the
  affiliation line and any required acknowledgement come from this review.
  That decision is downstream of this clearance.
