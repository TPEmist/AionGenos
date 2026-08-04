"""WP1 contact test-bed — OSC (Operational Space Control) bimanual env.

NEW task family (Paper 2, WP1-① closed-loop contact control). Uses
OperationalSpaceControllerActionCfg instead of DifferentialIK, per PI
decision Q1 (2026-08-03): OSC only for new L4+ contact tasks; L0-L3 stay
on DiffIK, untouched. Controller choice is pinned in
docs/p2_prereg/wp1_controller_provenance.md BEFORE any data collection.
"""
