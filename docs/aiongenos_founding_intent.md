# AionGenos — Founding Intent (precise statement)

> Archival record of a scope/philosophy ruling (two rounds of PI + user
> discussion). The narrative below is settled; this document files it, it does
> not re-open it. Companion: [harness_grant_ledger.md](./harness_grant_ledger.md).

## The "zero" is ZERO DEMONSTRATIONS, not zero priors

AionGenos learns bimanual manipulation with **zero demonstrations** — no
teleop trajectories, no imitation targets, no human-authored action sequences.
That is the claim.

It is **not** a zero-priors / blank-slate claim, and never was. The birth
configuration is, by deliberate architectural choice on day one:

> **a brain that has read every book (a pretrained VLM) + a new body.**

The pretrained VLM is a prior — an enormous one — and keeping it is not a
compromise of the thesis, it *is* the thesis. A blank slate was rejected at
the first architecture decision (teacher–student distillation and VLM
scaffolding both presuppose the brain is pretrained). The novelty is not
"learn from nothing"; it is "acquire the **body-grounded, situation-conditioned
control knowledge** with no demonstrations of that control."

## The core commitment: conditional knowledge must be EARNED

The dividing line the whole project is built to defend:

- **Conditional knowledge** — every mapping of the form *situation → action*
  ("this cube here → push from behind along that vector", "this contact state
  → this force") — **must be acquired through experience.** It may not be
  injected. This is what "zero demonstrations" protects: the situation→action
  map is exactly what a demonstration would hand over for free, and we refuse
  it.

- **Situation-independent mechanical common sense** (marginal, in the P1
  sense) — facts true regardless of the specific task instance — **may be
  supplied by the harness.** A standby posture, the kinematic form of a reach
  primitive, the existence of a work surface: these carry no information about
  *which* situation calls for *which* action, so granting them does not leak
  the thing we are trying to make the system earn.

The distinction is P1's **marginal vs conditional** framing applied to the
body (see the P1 confirmatory report §5.1 — self-reference intended). Marginal
= situation-independent = grantable. Conditional = situation-dependent = must
be earned.

### The auditability constraint (the core guard)

The marginal/conditional line is only as honest as it is **auditable**.
"Mechanical common sense" is a standing temptation to smuggle conditional
knowledge in through the back door — a "standby pose" that happens to encode
where objects usually are, a "primitive" whose default parameters happen to
solve the task. To keep the line falsifiable, **every harness grant must be
logged with an explicit reclamation condition** — the future experiment that
converts it back into a learning target. A grant with no reclamation path is
indistinguishable from an injected answer. This is why the
[harness_grant_ledger.md](./harness_grant_ledger.md) exists: it turns the
dividing line into a set of falsifiable promises rather than a matter of
taste.

## The infant analogy (precise version)

A newborn is not a blank slate either. It is born with **reflexes and flexor
muscle tone** — situation-independent motor priors that make the body a viable
platform for learning, without telling it what to *do* with the body.
Evolution is the infant's harness: it supplied the reflexes; it did not supply
the conditional map from a specific rattle's position to a specific reach.

The correspondence:

| Infant | AionGenos |
|--------|-----------|
| brain wired by evolution to learn | pretrained VLM (read every book) |
| reflexes / flexor muscle tone (marginal) | **standby pose = the machine's muscle tone** |
| evolution (supplied the reflexes) | the harness (supplies marginal common sense) |
| learning which action for which situation | earned conditional knowledge (zero-demo) |

The standby pose is the machine's flexor tone: a situation-independent default
configuration that makes the body ready, without encoding any situation→action
knowledge. Granting it is the analogue of being born with muscle tone, not the
analogue of being shown how to reach.

## What this rules in and out (operational)

- IN (harness may grant, marginal): standby/init posture; the kinematic form
  of hover-descend / approach-behind primitives; the existence and height of a
  work surface; frame conventions and coordinate plumbing.
- OUT (must be earned, conditional): which object to act on; when to descend /
  approach / push; contact-force targets; the parameters that tune a primitive
  to a specific situation; any situation→action mapping.
- Every IN item is entered in the Ledger with a reclamation condition. No
  grant is permanent by fiat; each is a debt with a stated experiment that
  repays it.
