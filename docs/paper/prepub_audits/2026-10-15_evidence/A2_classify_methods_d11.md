| row | file:line | token | class | evidence/source (absolute path:line + snippet) | note |
|---|---|---|---|---|---|
| 1 | arxiv/sections/methods_d11.tex:9 | 3 | D | Section header label (\section*{3. Methods}) | Section number |
| 2 | arxiv/sections/methods_d11.tex:11 | 3.1 | D | Subsection header label (\subsection*{3.1 Task and environment}) | Subsection number |
| 3 | arxiv/sections/methods_d11.tex:17 | 0.05 | D | Task success predicate threshold: scored arm within 0.05 m of target (docs/d11_preregistration.md \S2) | Success distance threshold (0.05 m) |
| 4 | arxiv/sections/methods_d11.tex:18 | 24 | D | Environment timeout constant: 24 s environment time-out limit (docs/d11_preregistration.md \S2; Amendment 15 pin 8) | Time-out budget (24 s) |
| 5 | arxiv/sections/methods_d11.tex:24 | 3.2 | D | Subsection header label (\subsection*{3.2 Teacher and memory pipeline}) | Subsection number |
| 6 | arxiv/sections/methods_d11.tex:26 | 4 | D | Teacher model architecture family (Gemma-4; docs/d11_preregistration.md \S3.1) | Teacher model family |
| 7 | arxiv/sections/methods_d11.tex:26 | 31 | D | Teacher model parameter size: 31B parameters (docs/d11_preregistration.md \S3.1) | Model parameter count (31B) |
| 8 | arxiv/sections/methods_d11.tex:26 | 4 | D | Teacher model quantization precision: 4-bit (bitsandbytes QLoRA; docs/d11_preregistration.md \S3.1) | Quantization precision (4-bit) |
| 9 | arxiv/sections/methods_d11.tex:28 | 1 | D | Interaction protocol round index: round 1 (docs/d11_preregistration.md \S3.1) | Protocol round index |
| 10 | arxiv/sections/methods_d11.tex:40 | 3.3 | D | Subsection header label (\subsection*{3.3 Students, arms, and the 2$\times$2 factorial}) | Subsection number |
| 11 | arxiv/sections/methods_d11.tex:40 | 2 | D | Experimental design factor count: 2$\times$2 factorial (first factor dimension) | Factorial design dimension (2) |
| 12 | arxiv/sections/methods_d11.tex:40 | 2 | D | Experimental design factor count: 2$\times$2 factorial (second factor dimension) | Factorial design dimension (2) |
| 13 | arxiv/sections/methods_d11.tex:42 | 16 | D | Architecture design constant: LoRA rank-16 adapter capacity (docs/d11_preregistration.md \S3.2) | Model capacity design parameter (rank-16) |
| 14 | arxiv/sections/methods_d11.tex:42 | 32 | D | Architecture design constant: LoRA scaling hyperparameter $\alpha$=32 (docs/d11_preregistration.md \S3.2) | LoRA alpha hyperparameter (32) |
| 15 | arxiv/sections/methods_d11.tex:42 | 0.05 | D | Architecture design constant: LoRA dropout probability 0.05 (docs/d11_preregistration.md \S3.2) | LoRA dropout hyperparameter (0.05) |
| 16 | arxiv/sections/methods_d11.tex:43 | 4 | D | Student base model architecture family (Gemma-4; docs/d11_preregistration.md \S3.2) | Student base model family |
| 17 | arxiv/sections/methods_d11.tex:43 | 31 | D | Student base model parameter size: 31B parameters (docs/d11_preregistration.md \S3.2) | Model parameter count (31B) |
| 18 | arxiv/sections/methods_d11.tex:46 | 4 | D | Training stage identifier label: Stage 4-A (docs/d11_preregistration.md \S3.2) | Training stage label |
| 19 | arxiv/sections/methods_d11.tex:46 | 992 | M | /home/control/AionGenos/docs/d11_preregistration.md:36: 'v4_sft_A (n=992)' (also line 921: '992 desirable + 1799 undesirable', line 1457: 'all 992 desirable and 1,810 undesirable samples enter training') | Measured desirable training rounds sample size (992) |
| 20 | arxiv/sections/methods_d11.tex:47 | 1 | D | Training schedule constant: 1 training epoch for Stage 4-A SFT (docs/d11_preregistration.md \S3.2) | Epoch count (1) |
| 21 | arxiv/sections/methods_d11.tex:47 | 2 | D | Training hyperparameter: Stage 4-A SFT learning rate mantissa (2e-4; docs/d11_preregistration.md \S3.2) | Learning rate mantissa (2e-4) |
| 22 | arxiv/sections/methods_d11.tex:47 | 4 | D | Training hyperparameter: Stage 4-A SFT learning rate exponent (2e-4; docs/d11_preregistration.md \S3.2) | Learning rate exponent (2e-4) |
| 23 | arxiv/sections/methods_d11.tex:48 | 4 | D | Training stage identifier label: Stage 4-B (docs/d11_preregistration.md \S3.2) | Training stage label |
| 24 | arxiv/sections/methods_d11.tex:48 | 992 | R | arxiv/sections/methods_d11.tex:46: 'SFT (stage 4-A, 992 desirable' | Repeat of desirable training rounds pool size (992; underlying M: docs/d11_preregistration.md:36) |
| 25 | arxiv/sections/methods_d11.tex:48 | 1799 | M | /home/control/AionGenos/docs/d11_preregistration.md:921: 'Amendment 8 §8.6 pinned all four training arms to the SAME 2791-row pool (992 desirable + 1799 undesirable' (also line 1376: 'old 1810 → new 1799, lost 11') | Measured undesirable training rounds pool size (1799) |
| 26 | arxiv/sections/methods_d11.tex:48 | 1 | D | Training schedule constant: 1 training epoch for Stage 4-B KTO (docs/d11_preregistration.md \S3.2) | Epoch count (1) |
| 27 | arxiv/sections/methods_d11.tex:48 | 5 | D | Training hyperparameter: Stage 4-B KTO learning rate mantissa (5e-5; docs/d11_preregistration.md \S3.2) | Learning rate mantissa (5e-5) |
| 28 | arxiv/sections/methods_d11.tex:48 | 5 | D | Training hyperparameter: Stage 4-B KTO learning rate exponent (5e-5; docs/d11_preregistration.md \S3.2) | Learning rate exponent (5e-5) |
| 29 | arxiv/sections/methods_d11.tex:49 | 0.1 | D | KTO loss hyperparameter: $\beta$=0.1 (docs/d11_preregistration.md \S3.2) | KTO loss weight beta (0.1) |
| 30 | arxiv/sections/methods_d11.tex:54 | 2 | D | Experimental design factor count: 2$\times$2 factorial (first factor dimension) | Factorial design dimension (2) |
| 31 | arxiv/sections/methods_d11.tex:54 | 2 | D | Experimental design factor count: 2$\times$2 factorial (second factor dimension) | Factorial design dimension (2) |
| 32 | arxiv/sections/methods_d11.tex:72 | 2791 | M | /home/control/AionGenos/docs/d11_preregistration.md:551: 'KTO_EXPECTED_ROWS = 2791 rows. This is the Amendment-8 §8.6 \"same 2791-row pool across all four arms\" invariant.' (also line 920: 'SAME 2791-row pool (992 desirable + 1799 undesirable)') | Measured total pinned training pool size (2791) |
| 33 | arxiv/sections/methods_d11.tex:72 | 992 | R | arxiv/sections/methods_d11.tex:46: 'SFT (stage 4-A, 992 desirable' | Repeat of desirable training rounds pool size (992; underlying M: docs/d11_preregistration.md:36) |
| 34 | arxiv/sections/methods_d11.tex:73 | 1799 | R | arxiv/sections/methods_d11.tex:48: '992 desirable + 1799 undesirable rounds' | Repeat of undesirable training rounds pool size (1799; underlying M: docs/d11_preregistration.md:921) |
| 35 | arxiv/sections/methods_d11.tex:73 | 256 | D | Cryptographic hash algorithm bit width: SHA-256 (Amendment 11/12) | Hash algorithm bit length (256) |
| 36 | arxiv/sections/methods_d11.tex:74 | 12 | D | Protocol amendment range lower bound: Amendment 12 (docs/paper/amendments) | Amendment number |
| 37 | arxiv/sections/methods_d11.tex:74 | 13 | D | Protocol amendment range upper bound: Amendment 13 (docs/paper/amendments) | Amendment number |
| 38 | arxiv/sections/methods_d11.tex:77 | 3.4 | D | Subsection header label (\subsection*{3.4 Evaluation protocols}) | Subsection number |
| 39 | arxiv/sections/methods_d11.tex:79 | 100 | D | Pre-registration protocol constant: sample size n=100 episodes per protocol (docs/d11_preregistration.md \S3.4) | Sample size n=100 |
| 40 | arxiv/sections/methods_d11.tex:108 | 8 | D | Protocol amendment label: Amendment 8 (docs/paper/amendments) | Amendment number |
| 41 | arxiv/sections/methods_d11.tex:112 | 12 | D | Protocol amendment range lower bound: Amendment 12 (docs/paper/amendments) | Amendment number |
| 42 | arxiv/sections/methods_d11.tex:112 | 13 | D | Protocol amendment range upper bound: Amendment 13 (docs/paper/amendments) | Amendment number |
| 43 | arxiv/sections/methods_d11.tex:114 | 4500 | D | Pre-registration protocol constant: base environment random seed 4500 (Amendment 11; docs/d11_preregistration.md \S3.4) | Base random seed (4500) |
| 44 | arxiv/sections/methods_d11.tex:115 | 4500 | D | Pre-registration protocol constant: per-episode seed offset formula 4500 (Amendment 11; docs/d11_preregistration.md \S3.4) | Seed offset constant (4500) |
| 45 | arxiv/sections/methods_d11.tex:117 | 11 | D | Protocol amendment label: Amendment 11 (docs/paper/amendments) | Amendment number |
| 46 | arxiv/sections/methods_d11.tex:119 | 3.5 | D | Subsection header label (\subsection*{3.5 Pre-registered hypotheses and tests}) | Subsection number |
| 47 | arxiv/sections/methods_d11.tex:122 | 9 | D | Protocol amendment range lower bound: Amendment 9 (docs/paper/amendments) | Amendment number |
| 48 | arxiv/sections/methods_d11.tex:122 | 10 | D | Protocol amendment range upper bound: Amendment 10 (docs/paper/amendments) | Amendment number |
| 49 | arxiv/sections/methods_d11.tex:125 | 10 | D | Pre-registered hypothesis decision threshold: T1 rejection threshold $\ge$+10 pp (Amendment 9 \S9.1; docs/d11_preregistration.md \S4) | Hypothesis decision threshold (+10 pp) |
| 50 | arxiv/sections/methods_d11.tex:126 | 0.020 | D | Pre-registered significance level for T1: $\alpha$=0.020 (Amendment 10 \S10.2; docs/d11_preregistration.md \S4) | Significance level (\alpha=0.020) |
| 51 | arxiv/sections/methods_d11.tex:127 | 10 | D | Pre-registered graded test threshold: T1-strong threshold $\ge$+10 pp (Amendment 9 \S9.1) | Graded threshold (+10 pp) |
| 52 | arxiv/sections/methods_d11.tex:127 | 0 | D | Pre-registered graded test threshold: T1-weak direction threshold $>0$ (Amendment 9 \S9.1) | Graded threshold direction (0) |
| 53 | arxiv/sections/methods_d11.tex:128 | 0.010 | D | Pre-registered significance level for T1-weak: $\alpha$=0.010 (Amendment 9 \S9.1 / Amendment 10 \S10.2) | Significance level (\alpha=0.010) |
| 54 | arxiv/sections/methods_d11.tex:130 | 0.020 | D | Pre-registered significance level for T1a: $\alpha$=0.020 (Amendment 10 \S10.2) | Significance level (\alpha=0.020) |
| 55 | arxiv/sections/methods_d11.tex:131 | 0.010 | D | Pre-registered significance level for T4: $\alpha$=0.010 (Amendment 10 \S10.2) | Significance level (\alpha=0.010) |
| 56 | arxiv/sections/methods_d11.tex:132 | 0.7 | D | Pre-registered transfer threshold multiplier: 0.7$\times$ pooled memory-teacher SR (docs/d11_preregistration.md \S4) | Retention threshold multiplier (0.7) |
| 57 | arxiv/sections/methods_d11.tex:132 | 36.2 | D | Pre-registered transfer floor product: 0.7 \times 51.7% = 36.2% (docs/d11_preregistration.md \S4; Amendment 10) | Calculated floor SR threshold (36.2%) |
| 58 | arxiv/sections/methods_d11.tex:134 | 0.060 | D | Family-wise error rate budget: $\alpha$=0.060 (Amendment 10 \S10.2) | Family-wise alpha budget (0.060) |
| 59 | arxiv/sections/methods_d11.tex:134 | 10 | D | Protocol amendment label: Amendment 10 (docs/paper/amendments) | Amendment number |
| 60 | arxiv/sections/methods_d11.tex:136 | 9 | D | Protocol amendment label: Amendment 9 (docs/paper/amendments) | Amendment number |
| 61 | arxiv/sections/methods_d11.tex:136 | 14 | D | Protocol amendment label: Amendment 14 (docs/paper/amendments) | Amendment number |
| 62 | arxiv/sections/methods_d11.tex:137 | 1 | D | Interaction protocol round index: round 1 (docs/d11_preregistration.md \S3.1) | Protocol round index |
| 63 | arxiv/sections/methods_d11.tex:140 | 16 | D | Protocol amendment label: Amendment 16 (docs/paper/amendments) | Amendment number |
| 64 | arxiv/sections/methods_d11.tex:141 | 23.5 | M | /home/control/AionGenos/workspace/d11_audit/d11_exploratory_report.txt:6: 'ref: D6=-23.5 mem-teacher=-15.8' (also /home/control/AionGenos/docs/d11_preregistration.md:79: '- D6 memoryless teacher: **−23.5 cm**') | Measured D6 memoryless teacher R1 dX fingerprint (-23.5) |
| 65 | arxiv/sections/methods_d11.tex:141 | 15.8 | M | /home/control/AionGenos/workspace/d11_audit/d11_exploratory_report.txt:6: 'ref: D6=-23.5 mem-teacher=-15.8' (also /home/control/AionGenos/docs/d11_preregistration.md:80: '- Memory-teacher last quartile (D10 ep 76-100): **−15.8 cm**') | Measured memory-teacher R1 dX fingerprint (-15.8) |
| 66 | arxiv/sections/methods_d11.tex:143 | 15 | D | Protocol amendment label: Amendment 15 (docs/paper/amendments) | Amendment number |
| 67 | arxiv/sections/methods_d11.tex:143 | 8 | D | Protocol amendment pin index: pin 8 (Amendment 15) | Amendment pin index |
| 68 | arxiv/sections/methods_d11.tex:144 | 2026 | D | Date component: year (2026) | Date year |
| 69 | arxiv/sections/methods_d11.tex:144 | 10 | D | Date component: month (10) | Date month |
| 70 | arxiv/sections/methods_d11.tex:144 | 05 | D | Date component: day (05) | Date day |
| 71 | arxiv/sections/methods_d11.tex:144 | 15 | D | Protocol amendment label: Amendment 15 (docs/paper/amendments) | Amendment number |
| 72 | arxiv/sections/methods_d11.tex:144 | 24 | D | Environment timeout constant: 24 s environment time-out limit (Amendment 15 pin 8; docs/d11_preregistration.md \S2) | Time-out budget (24 s) |
| 73 | arxiv/sections/methods_d11.tex:145 | 720 | D | Environment timeout step count: 720 steps at 30 Hz (Amendment 15 pin 8) | Environment step count limit (720) |
| 74 | arxiv/sections/methods_d11.tex:147 | 718 | M | /home/control/AionGenos/docs/paper/a15_p1_disclosure_pack.md:48: 'the boundary is index 718 in every episode' (also /home/control/AionGenos/docs/paper/a15_ab_results.md:134: '- Boundary: index 718 in every episode') | Measured step index of IsaacLab auto-reset boundary (index 718) |
| 75 | arxiv/sections/methods_d11.tex:154 | 3.6 | D | Subsection header label (\subsection*{3.6 Analysis rules (locked post-collection, pre-p-value)}) | Subsection number |
| 76 | arxiv/sections/methods_d11.tex:157 | 14 | D | Protocol amendment label: Amendment 14 (docs/paper/amendments) | Amendment number |
| 77 | arxiv/sections/methods_d11.tex:161 | 5 | D | Protocol diagnostic design constant: 5-way comparison across five protocols (Amendment 14) | Protocol comparison dimension (5) |
| 78 | arxiv/sections/methods_d11.tex:162 | 1 | D | Pairing gate numeric tolerance mantissa: 1e-4 m (Amendment 14 \S14.1) | Tolerance mantissa (1e-4) |
| 79 | arxiv/sections/methods_d11.tex:162 | 4 | D | Pairing gate numeric tolerance exponent: 1e-4 m (Amendment 14 \S14.1) | Tolerance exponent (1e-4) |
| 80 | arxiv/sections/methods_d11.tex:171 | 100 | M | /home/control/AionGenos/workspace/d11_audit/d11_confirmatory_report.txt:27: 'seed identical (5-way):            100/100' | Measured frozen-arm diagnostic identical seeds count (100/100) |
| 81 | arxiv/sections/methods_d11.tex:171 | 100 | D | Pre-registration protocol constant: sample size denominator n=100 per arm | Sample size denominator (100) |
| 82 | arxiv/sections/methods_d11.tex:172 | 100 | M | /home/control/AionGenos/workspace/d11_audit/d11_confirmatory_report.txt:28: 'frozen right-arm identical @ t0:   100/100' | Measured frozen right-arm identical states count (100/100) |
| 83 | arxiv/sections/methods_d11.tex:172 | 100 | D | Pre-registration protocol constant: sample size denominator n=100 per arm | Sample size denominator (100) |
| 84 | arxiv/sections/methods_d11.tex:172 | 1 | M | /home/control/AionGenos/workspace/d11_audit/d11_confirmatory_report.txt:29: 'active left-arm identical @ t0:    1/100' | Measured active left-arm identical states count (1/100) |
| 85 | arxiv/sections/methods_d11.tex:172 | 100 | D | Pre-registration protocol constant: sample size denominator n=100 per arm | Sample size denominator (100) |
| 86 | arxiv/sections/methods_d11.tex:175 | 1 | D | Table reference label (Table 1) | Table number |
| 87 | arxiv/sections/methods_d11.tex:177 | 3.7 | D | Subsection header label (\subsection*{3.7 Data curation and its honest history}) | Subsection number |
| 88 | arxiv/sections/methods_d11.tex:183 | 13 | D | Protocol amendment label: Amendment 13 (docs/paper/amendments) | Amendment number |
| 89 | arxiv/sections/methods_d11.tex:185 | 992 | R | arxiv/sections/methods_d11.tex:46: 'SFT (stage 4-A, 992 desirable' | Repeat of desirable training pool count (992; underlying M: docs/d11_preregistration.md:36) |
| 90 | arxiv/sections/methods_d11.tex:185 | 2791 | R | arxiv/sections/methods_d11.tex:72: 'identical 2791-round pool' | Repeat of total training pool count (2791; underlying M: docs/d11_preregistration.md:551) |
| 91 | arxiv/sections/methods_d11.tex:193 | 1 | D | Protocol amendment range lower bound: Amendment 1 (docs/paper/amendments) | Amendment number |
| 92 | arxiv/sections/methods_d11.tex:193 | 13 | D | Protocol amendment range upper bound: Amendment 13 (docs/paper/amendments) | Amendment number |
| 93 | arxiv/sections/methods_d11.tex:194 | 14 | D | Protocol amendment label: Amendment 14 (docs/paper/amendments) | Amendment number |
| 94 | arxiv/sections/methods_d11.tex:200 | 6.6 | D | LaTeX table column layout dimension: 6.6cm width | Table column dimension (6.6cm) |
| 95 | arxiv/sections/methods_d11.tex:200 | 2.6 | D | LaTeX table column layout dimension: 2.6cm width | Table column dimension (2.6cm) |
| 96 | arxiv/sections/methods_d11.tex:204 | 1 | D | Amendment table index: Amendment 1 | Amendment number |
| 97 | arxiv/sections/methods_d11.tex:204 | 07 | D | Date component: month (07) | Date month |
| 98 | arxiv/sections/methods_d11.tex:204 | 06 | D | Date component: day (06) | Date day |
| 99 | arxiv/sections/methods_d11.tex:205 | 2 | D | Amendment table index: Amendment 2 | Amendment number |
| 100 | arxiv/sections/methods_d11.tex:205 | 07 | D | Date component: month (07) | Date month |
| 101 | arxiv/sections/methods_d11.tex:205 | 06 | D | Date component: day (06) | Date day |
| 102 | arxiv/sections/methods_d11.tex:205 | 85 | D | Protocol escalation threshold: agreement <85% triggers LLM judge (Amendment 2) | Audit escalation agreement threshold (85%) |
| 103 | arxiv/sections/methods_d11.tex:206 | 3 | D | Amendment table index: Amendment 3 | Amendment number |
| 104 | arxiv/sections/methods_d11.tex:206 | 07 | D | Date component: month (07) | Date month |
| 105 | arxiv/sections/methods_d11.tex:206 | 06 | D | Date component: day (06) | Date day |
| 106 | arxiv/sections/methods_d11.tex:207 | 4 | D | Amendment table index: Amendment 4 | Amendment number |
| 107 | arxiv/sections/methods_d11.tex:207 | 07 | D | Date component: month (07) | Date month |
| 108 | arxiv/sections/methods_d11.tex:207 | 07 | D | Date component: day (07) | Date day |
| 109 | arxiv/sections/methods_d11.tex:207 | 1 | D | Rationale filter rule index: Rule 1 (Amendment 4; docs/d11_preregistration.md \S6) | Filter rule index |
| 110 | arxiv/sections/methods_d11.tex:208 | 5 | D | Amendment table index: Amendment 5 | Amendment number |
| 111 | arxiv/sections/methods_d11.tex:208 | 07 | D | Date component: month (07) | Date month |
| 112 | arxiv/sections/methods_d11.tex:208 | 07 | D | Date component: day (07) | Date day |
| 113 | arxiv/sections/methods_d11.tex:208 | 2 | D | Rationale filter rule index: Rule 2 (Amendment 5; docs/d11_preregistration.md \S6) | Filter rule index |
| 114 | arxiv/sections/methods_d11.tex:209 | 6 | D | Amendment table index: Amendment 6 | Amendment number |
| 115 | arxiv/sections/methods_d11.tex:209 | 07 | D | Date component: month (07) | Date month |
| 116 | arxiv/sections/methods_d11.tex:209 | 07 | D | Date component: day (07) | Date day |
| 117 | arxiv/sections/methods_d11.tex:209 | 992 | R | arxiv/sections/methods_d11.tex:46: 'SFT (stage 4-A, 992 desirable' | Repeat of desirable training pool count (992; underlying M: docs/d11_preregistration.md:36) |
| 118 | arxiv/sections/methods_d11.tex:209 | 1810 | M | /home/control/AionGenos/docs/d11_preregistration.md:1457: 'all 992 desirable and 1,810 undesirable samples enter training' (also line 1361: '992 desirable + 1810 undesirable', line 1376: 'old 1810 → new 1799') | Measured pre-Amendment 8 undesirable training rounds pool size (1810) |
| 119 | arxiv/sections/methods_d11.tex:210 | 7 | D | Amendment table index: Amendment 7 | Amendment number |
| 120 | arxiv/sections/methods_d11.tex:210 | 07 | D | Date component: month (07) | Date month |
| 121 | arxiv/sections/methods_d11.tex:210 | 08 | D | Date component: day (08) | Date day |
| 122 | arxiv/sections/methods_d11.tex:211 | 8 | D | Amendment table index: Amendment 8 | Amendment number |
| 123 | arxiv/sections/methods_d11.tex:211 | 07 | D | Date component: month (07) | Date month |
| 124 | arxiv/sections/methods_d11.tex:211 | 08 | D | Date component: day (08) | Date day |
| 125 | arxiv/sections/methods_d11.tex:211 | 2 | D | Experimental design factor count: 2$\times$2 factorial (first factor dimension) | Factorial design dimension (2) |
| 126 | arxiv/sections/methods_d11.tex:211 | 2 | D | Experimental design factor count: 2$\times$2 factorial (second factor dimension) | Factorial design dimension (2) |
| 127 | arxiv/sections/methods_d11.tex:212 | 9 | D | Amendment table index: Amendment 9 | Amendment number |
| 128 | arxiv/sections/methods_d11.tex:212 | 07 | D | Date component: month (07) | Date month |
| 129 | arxiv/sections/methods_d11.tex:212 | 08 | D | Date component: day (08) | Date day |
| 130 | arxiv/sections/methods_d11.tex:213 | 10 | D | Amendment table index: Amendment 10 | Amendment number |
| 131 | arxiv/sections/methods_d11.tex:213 | 07 | D | Date component: month (07) | Date month |
| 132 | arxiv/sections/methods_d11.tex:213 | 08 | D | Date component: day (08) | Date day |
| 133 | arxiv/sections/methods_d11.tex:214 | 11 | D | Amendment table index: Amendment 11 | Amendment number |
| 134 | arxiv/sections/methods_d11.tex:214 | 07 | D | Date component: month (07) | Date month |
| 135 | arxiv/sections/methods_d11.tex:214 | 08 | D | Date component: day (08) | Date day |
| 136 | arxiv/sections/methods_d11.tex:214 | 4500 | D | Pre-registration protocol constant: base environment random seed 4500 (Amendment 11; docs/d11_preregistration.md \S3.4) | Base random seed (4500) |
| 137 | arxiv/sections/methods_d11.tex:215 | 12 | D | Amendment table index: Amendment 12 | Amendment number |
| 138 | arxiv/sections/methods_d11.tex:215 | 07 | D | Date component: month (07) | Date month |
| 139 | arxiv/sections/methods_d11.tex:215 | 08 | D | Date component: day (08) | Date day |
| 140 | arxiv/sections/methods_d11.tex:216 | 13 | D | Amendment table index: Amendment 13 | Amendment number |
| 141 | arxiv/sections/methods_d11.tex:216 | 07 | D | Date component: month (07) | Date month |
| 142 | arxiv/sections/methods_d11.tex:216 | 08 | D | Date component: day (08) | Date day |
| 143 | arxiv/sections/methods_d11.tex:216 | 2 | D | Pipeline processing step index label: Step-2 (Amendment 13) | Pipeline step index |
| 144 | arxiv/sections/methods_d11.tex:217 | 14 | D | Amendment table index: Amendment 14 | Amendment number |
| 145 | arxiv/sections/methods_d11.tex:217 | 07 | D | Date component: month (07) | Date month |
| 146 | arxiv/sections/methods_d11.tex:217 | 13 | D | Date component: day (13) | Date day |
| 147 | arxiv/sections/methods_d11.tex:222 | 5 | D | Protocol amendment range lower bound: Amendment 5 (docs/paper/amendments) | Amendment number |
| 148 | arxiv/sections/methods_d11.tex:222 | 13 | D | Protocol amendment range upper bound: Amendment 13 (docs/paper/amendments) | Amendment number |
| 149 | arxiv/sections/methods_d11.tex:222 | 07 | D | Date component: month (07) | Date month |
| 150 | arxiv/sections/methods_d11.tex:222 | 07 | D | Date component: day (07) | Date day |
| 151 | arxiv/sections/methods_d11.tex:222 | 07 | D | Date component: month (07) | Date month |
| 152 | arxiv/sections/methods_d11.tex:222 | 08 | D | Date component: day (08) | Date day |
| 153 | arxiv/sections/methods_d11.tex:227 | 992 | R | arxiv/sections/methods_d11.tex:46: 'SFT (stage 4-A, 992 desirable' | Repeat of desirable training pool count (992; underlying M: docs/d11_preregistration.md:36) |
| 154 | arxiv/sections/methods_d11.tex:227 | 1799 | R | arxiv/sections/methods_d11.tex:48: '992 desirable + 1799 undesirable rounds' | Repeat of undesirable training pool count (1799; underlying M: docs/d11_preregistration.md:921) |
| 155 | arxiv/sections/methods_d11.tex:227 | 8 | D | Protocol amendment label: Amendment 8 (docs/paper/amendments) | Amendment number |
| 156 | arxiv/sections/methods_d11.tex:227 | 992 | R | arxiv/sections/methods_d11.tex:46: 'SFT (stage 4-A, 992 desirable' | Repeat of desirable training pool count (992; underlying M: docs/d11_preregistration.md:36) |
| 157 | arxiv/sections/methods_d11.tex:227 | 1810 | R | arxiv/sections/methods_d11.tex:209: '(v-final 992+1810)' | Repeat of pre-Amendment 8 undesirable training pool count (1810; underlying M: docs/d11_preregistration.md:1457) |
| 158 | arxiv/sections/methods_d11.tex:228 | 11 | M | /home/control/AionGenos/docs/d11_preregistration.md:1376: '- v_final_kto_B undesirable: old 1810 → new 1799, lost 11 (subset relation verified: all 1799 IDs in new exist in old 1810; 11 lost are exactly the ones without matching teacher recap)' | Measured count of no-retrieval-hit rounds removed by trajectory ID diff (11) |
| 159 | arxiv/sections/methods_d11.tex:229 | 1799 | R | arxiv/sections/methods_d11.tex:48: '992 desirable + 1799 undesirable rounds' | Repeat of final undesirable training pool count (1799; underlying M: docs/d11_preregistration.md:921) |
| 160 | arxiv/sections/methods_d11.tex:234 | 1 | D | Rationale filter rule range lower bound: Rule 1 (Amendment 4; docs/d11_preregistration.md \S6) | Filter rule index |
| 161 | arxiv/sections/methods_d11.tex:234 | 2 | D | Rationale filter rule range upper bound: Rule 2 (Amendment 5; docs/d11_preregistration.md \S6) | Filter rule index |
| 162 | arxiv/sections/methods_d11.tex:235 | 4 | D | Protocol amendment range lower bound: Amendment 4 (docs/paper/amendments) | Amendment number |
| 163 | arxiv/sections/methods_d11.tex:235 | 6 | D | Protocol amendment range upper bound: Amendment 6 (docs/paper/amendments) | Amendment number |
| 164 | arxiv/sections/methods_d11.tex:237 | 13 | D | Protocol amendment label: Amendment 13 (docs/paper/amendments) | Amendment number |
| 165 | arxiv/sections/methods_d11.tex:238 | 992 | R | arxiv/sections/methods_d11.tex:46: 'SFT (stage 4-A, 992 desirable' | Repeat of desirable training pool count (992; underlying M: docs/d11_preregistration.md:36) |
| 166 | arxiv/sections/methods_d11.tex:238 | 2791 | R | arxiv/sections/methods_d11.tex:72: 'identical 2791-round pool' | Repeat of total training pool count (2791; underlying M: docs/d11_preregistration.md:551) |
| 167 | arxiv/sections/appendix_amendments.tex:11 | 1 | D | Protocol amendment range lower bound: Amendment 1 (docs/paper/amendments) | Amendment number |
| 168 | arxiv/sections/appendix_amendments.tex:11 | 14 | D | Protocol amendment range upper bound: Amendment 14 (docs/paper/amendments) | Amendment number |
| 169 | arxiv/sections/appendix_amendments.tex:11 | 15 | D | Protocol amendment label: Amendment 15 (docs/paper/amendments) | Amendment number |
| 170 | arxiv/sections/appendix_amendments.tex:11 | 2026 | D | Date component: year (2026) | Date year |
| 171 | arxiv/sections/appendix_amendments.tex:11 | 10 | D | Date component: month (10) | Date month |
| 172 | arxiv/sections/appendix_amendments.tex:11 | 05 | D | Date component: day (05) | Date day |
| 173 | arxiv/sections/appendix_amendments.tex:13 | 16 | D | Protocol amendment label: Amendment 16 (docs/paper/amendments) | Amendment number |
| 174 | arxiv/sections/appendix_amendments.tex:13 | 2026 | D | Date component: year (2026) | Date year |
| 175 | arxiv/sections/appendix_amendments.tex:13 | 10 | D | Date component: month (10) | Date month |
| 176 | arxiv/sections/appendix_amendments.tex:13 | 05 | D | Date component: day (05) | Date day |
| 177 | arxiv/sections/appendix_amendments.tex:15 | 1 | D | Experiment index label: Experiment-1 (D11) | Experiment index |
| 178 | arxiv/sections/appendix_amendments.tex:16 | 1 | D | L2 amendment identifier: Amendment 1 (docs/paper/l2_amendments) | Amendment identifier |
| 179 | arxiv/sections/appendix_amendments.tex:16 | 1 | D | L2 amendment identifier sub-part: Amendment 1a (docs/paper/l2_amendments) | Amendment identifier |
| 180 | arxiv/sections/appendix_amendments.tex:16 | 2 | D | L2 amendment identifier: Amendment 2 (docs/paper/l2_amendments) | Amendment identifier |
| 181 | arxiv/sections/appendix_amendments.tex:16 | 3 | D | L2 amendment identifier: Amendment 3 (docs/paper/l2_amendments) | Amendment identifier |
| 182 | arxiv/sections/appendix_amendments.tex:17 | 2 | D | Experiment index label: Experiment-2 (L2) | Experiment index |
| 183 | arxiv/sections/related_work.tex:2 | 2 | D | Section header label (\section*{2. Related Work}) | Section number |
| 184 | arxiv/sections/related_work.tex:49 | 0.6 | D | External policy threshold / algorithm naming constant from literature: $\pi^{*}_{0.6}$ (pistar06_2025) | Algorithm naming parameter (0.6) |
| 185 | arxiv/sections/related_work.tex:70 | 1 | R | arxiv/sections/results_d11.tex:25: 'detectable effect: +1 pp (z=0.16, p=0.87, two-sided; Newcombe 95% CI' | Repeat of D11 T1 contrast (+1 pp; underlying M: derived_stats.txt:6) |
| 186 | arxiv/sections/related_work.tex:70 | 23 | R | arxiv/sections/results_d11.tex:103: '49/100 vs 26/100 --- +23 pp (z=3.36, p=7.8\times 10^{-4}' | Repeat of D11 T4 contrast (+23 pp; underlying M: derived_stats.txt:8 / d11_confirmatory_report.txt:55) |
| 187 | arxiv/sections/appendix_teacher_provenance.tex:9 | 2026 | D | Date component: year (2026) | Date year |
| 188 | arxiv/sections/appendix_teacher_provenance.tex:9 | 06 | D | Date component: month (06) | Date month |
| 189 | arxiv/sections/appendix_teacher_provenance.tex:9 | 08 | D | Date component: day (08) | Date day |
| 190 | arxiv/sections/appendix_teacher_provenance.tex:11 | 2026 | D | Date component: year (2026) | Date year |
| 191 | arxiv/sections/appendix_teacher_provenance.tex:11 | 07 | D | Date component: month (07) | Date month |
| 192 | arxiv/sections/appendix_teacher_provenance.tex:11 | 14 | D | Date component: day (14) | Date day |
| 193 | arxiv/sections/appendix_teacher_provenance.tex:11 | 4 | D | Teacher model architecture family (Gemma-4; docs/paper/d11_teacher_provenance.md:12) | Teacher model family |
| 194 | arxiv/sections/appendix_teacher_provenance.tex:11 | 31 | D | Teacher model parameter size: 31B parameters (docs/paper/d11_teacher_provenance.md:12) | Model parameter count (31B) |
| 195 | arxiv/sections/appendix_teacher_provenance.tex:12 | 16384 | D | Inference server configuration: context window size 16384 tokens (docs/paper/d11_teacher_provenance.md:13) | Context window size (16384) |
| 196 | arxiv/sections/appendix_teacher_provenance.tex:17 | 4 | D | Teacher training pipeline stage label: Stage-4 (docs/paper/d11_teacher_provenance.md:17) | Pipeline stage label |
| 197 | arxiv/sections/appendix_teacher_provenance.tex:21 | 547 | M | /home/control/audit/fab376a/docs/paper/birth_certificates/derived_stats.txt:35: '[target_color] frozen buffer 547 recaps: literal in instruction 547/547, in lesson 0/547; lesson names \'red\' 517/547' (also /home/control/audit/fab376a/docs/paper/d11_teacher_provenance.md:20: 'recaps_d10 = 547 records total across 7 runs') | Measured total recap records collected for D10 frozen buffer (547 records across 7 runs) |
| 198 | arxiv/sections/appendix_teacher_provenance.tex:21 | 7 | M | /home/control/audit/fab376a/docs/paper/d11_teacher_provenance.md:20: 'respectively (recaps_d10 = 547 records total across 7 runs).' | Measured number of data collection runs contributing to D10 recap pool (7 runs) |
| 199 | arxiv/sections/appendix_teacher_provenance.tex:22 | 8 | M | /home/control/audit/fab376a/docs/paper/d11_teacher_provenance.md:21: '- **L2 (dual-push) first collect:** inline recap failed 8/8 episodes, every one \"Empty content in VLM response\".' | Measured count of failed inline recap episodes during L2 first collect (8) |
| 200 | arxiv/sections/appendix_teacher_provenance.tex:22 | 8 | M | /home/control/audit/fab376a/docs/paper/d11_teacher_provenance.md:21: '- **L2 (dual-push) first collect:** inline recap failed 8/8 episodes, every one \"Empty content in VLM response\".' | Measured total episodes attempted in L2 first recap collection (8) |
| 201 | arxiv/sections/appendix_teacher_provenance.tex:27 | 2026 | D | Date component: year (2026) | Date year |
| 202 | arxiv/sections/appendix_teacher_provenance.tex:27 | 07 | D | Date component: month (07) | Date month |
| 203 | arxiv/sections/appendix_teacher_provenance.tex:27 | 14 | D | Date component: day (14) | Date day |
| 204 | arxiv/sections/appendix_teacher_provenance.tex:27 | 4 | D | Model architecture family (gemma-4; docs/paper/d11_teacher_provenance.md:24) | Model architecture family |
| 205 | arxiv/sections/appendix_teacher_provenance.tex:28 | 400 | D | Inference server token generation budget: 400-token output limit (docs/paper/d11_teacher_provenance.md:26) | Server output token budget (400) |
| 206 | arxiv/sections/appendix_teacher_provenance.tex:40 | 469 | M | /home/control/audit/fab376a/docs/paper/d11_teacher_provenance.md:38: 'returned empty now returns a real 469-char lesson in 7 s.' | Measured length of recovered lesson output under reasoning-off (469 characters) |
| 207 | arxiv/sections/appendix_teacher_provenance.tex:40 | 7 | M | /home/control/audit/fab376a/docs/paper/d11_teacher_provenance.md:38: 'returned empty now returns a real 469-char lesson in 7 s.' | Measured runtime latency duration for lesson generation under reasoning-off (7 s) |
| 208 | arxiv/sections/appendix_teacher_provenance.tex:41 | 512 | D | Inference server configuration parameter: reasoning-budget 512 tokens (docs/paper/d11_teacher_provenance.md:9) | Reasoning budget (512) |
| 209 | arxiv/sections/appendix_teacher_provenance.tex:46 | 512 | D | Inference server configuration parameter: reasoning-budget 512 tokens (docs/paper/d11_teacher_provenance.md:43) | Reasoning budget (512) |
| 210 | arxiv/sections/appendix_teacher_provenance.tex:47 | 0 | D | Inference server configuration parameter: reasoning-budget 0 tokens (docs/paper/d11_teacher_provenance.md:44) | Reasoning budget (0) |
| 211 | arxiv/sections/appendix_teacher_provenance.tex:53 | 1 | D | Teacher training pipeline stage label: Stage-1 (docs/paper/d11_teacher_provenance.md:49) | Pipeline stage label |
| 212 | arxiv/sections/appendix_teacher_provenance.tex:54 | 1 | D | Teacher training pipeline stage label: Stage-1 (docs/paper/d11_teacher_provenance.md:50) | Pipeline stage label |
| 213 | arxiv/sections/appendix_teacher_provenance.tex:63 | 4 | D | Teacher model architecture family (gemma-4; docs/paper/d11_teacher_provenance.md:56) | Model architecture family |
| 214 | arxiv/sections/appendix_teacher_provenance.tex:63 | 31 | D | Teacher model parameter size: 31B parameters (docs/paper/d11_teacher_provenance.md:56) | Model parameter count (31B) |
| 215 | arxiv/sections/appendix_teacher_provenance.tex:63 | 16384 | D | Inference server context window size: 16384 tokens (docs/paper/d11_teacher_provenance.md:56) | Context window size (16384) |
| 216 | arxiv/sections/appendix_teacher_provenance.tex:63 | 512 | D | Inference server configuration parameter: reasoning-budget 512 tokens (docs/paper/d11_teacher_provenance.md:56) | Reasoning budget (512) |
| 217 | arxiv/sections/appendix_teacher_provenance.tex:64 | 2026 | D | Date component: year (2026) | Date year |
| 218 | arxiv/sections/appendix_teacher_provenance.tex:64 | 07 | D | Date component: month (07) | Date month |
| 219 | arxiv/sections/appendix_teacher_provenance.tex:64 | 14 | D | Date component: day (14) | Date day |
| 220 | arxiv/sections/appendix_teacher_provenance.tex:64 | 0 | D | Inference server configuration parameter: reasoning-budget 0 tokens (docs/paper/d11_teacher_provenance.md:57) | Reasoning budget (0) |
