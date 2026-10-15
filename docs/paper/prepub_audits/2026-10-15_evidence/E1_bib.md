# TASK E1-bib: Pre-Publication Bibliography Audit Evidence Report

**Audit Date & Date of Fetch:** 2026-10-15  
**Audited Trees (Read-Only):** `/home/control/audit/fab376a` and `/home/control/audit/acfd91d` (git SHAs `fab376a` and `acfd91d`)  
**Audited Bibliography Files:**
- `/home/control/audit/fab376a/docs/paper/arxiv/refs.bib` (372 lines, 41 entries)
- `/home/control/audit/fab376a/docs/paper/bar/refs.bib` (372 lines, 41 entries; byte-identical to `arxiv/refs.bib`)

**Audit Scope and In-Prose Citation Rules:**
- For document `docs/paper/arxiv`: .tex files searched: `fab376a/docs/paper/arxiv/main.tex` and all `fab376a/docs/paper/arxiv/sections/*.tex`.
- For document `docs/paper/bar`: .tex files searched: `fab376a/docs/paper/bar/main.tex`.
- Total distinct entries audited: 41 entries per bib file.
- Citation counts in `docs/paper/arxiv`: 40 entries cited, 1 entry uncited (`ovadia2024ft`).
- Citation counts in `docs/paper/bar`: 21 entries cited, 20 entries uncited.

---

## 1. Entry `voyager2023`

- **Bib Key:** `voyager2023`
- **Bib File Locations:**
  * `/home/control/audit/fab376a/docs/paper/arxiv/refs.bib`: lines 7–12
  * `/home/control/audit/fab376a/docs/paper/bar/refs.bib`: lines 7–12
- **Cited in `docs/paper/arxiv`:** **Yes** (2 occurrences)
  * `fab376a/docs/paper/arxiv/sections/discussion.tex:63`: `behaviour/skill retrieval and episodic-memory agents (Voyager~\citep{voyager2023},`
  * `fab376a/docs/paper/arxiv/sections/related_work.tex:15`: `\paragraph{Agent memory and experiential learning.} Voyager~\citep{voyager2023},`
- **Cited in `docs/paper/bar`:** **Yes** (1 occurrence)
  * `fab376a/docs/paper/bar/main.tex:157`: `Agent-memory systems~\citep{voyager2023, expel2024, awm2024} and`

**BibTeX Entry as Written:**
```bibtex
7: @article{voyager2023,
8:   title   = {{Voyager: An Open-Ended Embodied Agent with Large Language Models}},
9:   author  = {Wang, Guanzhi and Xie, Yuqi and Jiang, Yunfan and Mandlekar, Ajay and Xiao, Chaowei and Zhu, Yuke and Fan, Linxi and Anandkumar, Anima},
10:   journal = {arXiv preprint arXiv:2305.16291},
11:   year    = {2023}
12: }
```

**Authoritative Metadata (Fetched 2026-10-15):**
- **Authoritative Title:** Voyager: An Open-Ended Embodied Agent with Large Language Models
- **Authoritative Authors (8 authors):** Guanzhi Wang, Yuqi Xie, Yunfan Jiang, Ajay Mandlekar, Chaowei Xiao, Yuke Zhu, Linxi Fan, Anima Anandkumar
- **Authoritative Venue:** Transactions on Machine Learning Research (TMLR)
- **Authoritative Year:** 2024
- **Authoritative URL:** https://openreview.net/forum?id=ehfRiF0R3a (also arXiv: https://arxiv.org/abs/2305.16291)
- **Formal Published Version Exists:** Yes (Transactions on Machine Learning Research, March 2024; ISSN 2835-8856)
- **Bib Cites Formal Published Version:** No (bib cites `arXiv preprint arXiv:2305.16291`, year 2023)
- **Mismatches / Discrepancies Verbatim:**
  * Venue: bib lists `journal = {arXiv preprint arXiv:2305.16291}`; authoritative published venue is `Transactions on Machine Learning Research (TMLR)`.
  * Year: bib lists `year = {2023}`; authoritative formal publication year is `2024`.
- **Date of Fetch:** 2026-10-15

---

## 2. Entry `titans2025`

- **Bib Key:** `titans2025`
- **Bib File Locations:**
  * `/home/control/audit/fab376a/docs/paper/arxiv/refs.bib`: lines 14–23
  * `/home/control/audit/fab376a/docs/paper/bar/refs.bib`: lines 14–23
- **Cited in `docs/paper/arxiv`:** **Yes** (1 occurrence)
  * `fab376a/docs/paper/arxiv/sections/discussion.tex:76`: `memory in general. Titans-style architectural writing~\citep{titans2025}`
- **Cited in `docs/paper/bar`:** **Yes** (1 occurrence)
  * `fab376a/docs/paper/bar/main.tex:166`: `memory~\citep{titans2025, seal2025} push the parametric one. We do not claim primacy for`

**BibTeX Entry as Written:**
```bibtex
14: @inproceedings{titans2025,
15:   title     = {{Titans: Learning to Memorize at Test Time}},
16:   author    = {Behrouz, Ali and Zhong, Peilin and Mirrokni, Vahab},
17:   booktitle = {Advances in Neural Information Processing Systems (NeurIPS)},
18:   volume    = {38},
19:   pages     = {125925--125962},
20:   year      = {2025},
21:   doi       = {10.52202/085713-3786},
22:   note      = {arXiv:2501.00663}
23: }
```

**Authoritative Metadata (Fetched 2026-10-15):**
- **Authoritative Title:** Titans: Learning to Memorize at Test Time
- **Authoritative Authors (3 authors):** Ali Behrouz, Peilin Zhong, Vahab Mirrokni
- **Authoritative Venue:** Advances in Neural Information Processing Systems 38 (NeurIPS 2024/2025), pages 125925-125962, DOI: 10.52202/085713-3786
- **Authoritative Year:** 2025
- **Authoritative URL:** https://doi.org/10.52202/085713-3786 (also arXiv: https://arxiv.org/abs/2501.00663)
- **Formal Published Version Exists:** Yes (Advances in Neural Information Processing Systems 38, 2025)
- **Bib Cites Formal Published Version:** Yes (bib cites NeurIPS 38, pages 125925--125962, DOI 10.52202/085713-3786, year 2025; note records arXiv:2501.00663)
- **Mismatches / Discrepancies Verbatim:**
  * None verbatim against Crossref metadata (bib appends note = {arXiv:2501.00663} and booktitle includes `(NeurIPS)` acronym).
- **Date of Fetch:** 2026-10-15

---

## 3. Entry `expel2024`

- **Bib Key:** `expel2024`
- **Bib File Locations:**
  * `/home/control/audit/fab376a/docs/paper/arxiv/refs.bib`: lines 25–31
  * `/home/control/audit/fab376a/docs/paper/bar/refs.bib`: lines 25–31
- **Cited in `docs/paper/arxiv`:** **Yes** (2 occurrences)
  * `fab376a/docs/paper/arxiv/sections/discussion.tex:64`: `ExpeL~\citep{expel2024}, AWM~\citep{awm2024}; ASPIRE~\citep{lu2026aspire})`
  * `fab376a/docs/paper/arxiv/sections/related_work.tex:16`: `ExpeL~\citep{expel2024}, and`
- **Cited in `docs/paper/bar`:** **Yes** (1 occurrence)
  * `fab376a/docs/paper/bar/main.tex:157`: `Agent-memory systems~\citep{voyager2023, expel2024, awm2024} and`

**BibTeX Entry as Written:**
```bibtex
25: @inproceedings{expel2024,
26:   title     = {{ExpeL: LLM Agents Are Experiential Learners}},
27:   author    = {Zhao, Andrew and Huang, Daniel and Xu, Quentin and Lin, Matthieu and Liu, Yong-Jin and Huang, Gao},
28:   booktitle = {Proceedings of the AAAI Conference on Artificial Intelligence (AAAI)},
29:   year      = {2024},
30:   note      = {arXiv:2308.10144}
31: }
```

**Authoritative Metadata (Fetched 2026-10-15):**
- **Authoritative Title:** ExpeL: LLM Agents Are Experiential Learners
- **Authoritative Authors (6 authors):** Andrew Zhao, Daniel Huang, Quentin Xu, Matthieu Lin, Yong-Jin Liu, Gao Huang
- **Authoritative Venue:** Proceedings of the AAAI Conference on Artificial Intelligence, Vol. 38, No. 17 (2024), pages 19632-19642, DOI: 10.1609/aaai.v38i17.29936
- **Authoritative Year:** 2024
- **Authoritative URL:** https://doi.org/10.1609/aaai.v38i17.29936 (also arXiv: https://arxiv.org/abs/2308.10144)
- **Formal Published Version Exists:** Yes (Proceedings of the AAAI Conference on Artificial Intelligence, 2024)
- **Bib Cites Formal Published Version:** Yes (bib cites AAAI proceedings 2024, but omits volume, issue, pages, and DOI; note records arXiv:2308.10144)
- **Mismatches / Discrepancies Verbatim:**
  * Volume, Issue, Pages, DOI omitted: bib omits volume `38`, issue `17`, pages `19632--19642`, and DOI `10.1609/aaai.v38i17.29936`.
- **Date of Fetch:** 2026-10-15

---

## 4. Entry `distillstepbystep2023`

- **Bib Key:** `distillstepbystep2023`
- **Bib File Locations:**
  * `/home/control/audit/fab376a/docs/paper/arxiv/refs.bib`: lines 33–41
  * `/home/control/audit/fab376a/docs/paper/bar/refs.bib`: lines 33–41
- **Cited in `docs/paper/arxiv`:** **Yes** (1 occurrence)
  * `fab376a/docs/paper/arxiv/sections/related_work.tex:66`: `\paragraph{Reasoning distillation.} Distilling Step-by-Step~\citep{distillstepbystep2023}, Embodied-CoT~\citep{embodiedcot2024}, and`
- **Cited in `docs/paper/bar`:** **Yes** (1 occurrence)
  * `fab376a/docs/paper/bar/main.tex:163`: `distillation~\citep{distillstepbystep2023}, experience-driven`

**BibTeX Entry as Written:**
```bibtex
33: @inproceedings{distillstepbystep2023,
34:   title     = {{Distilling Step-by-Step! Outperforming Larger Language Models with Less Training Data and Smaller Model Sizes}},
35:   author    = {Hsieh, Cheng-Yu and Li, Chun-Liang and Yeh, Chih-kuan and Nakhost, Hootan and Fujii, Yasuhisa and Ratner, Alex and Krishna, Ranjay and Lee, Chen-Yu and Pfister, Tomas},
36:   booktitle = {Findings of the Association for Computational Linguistics: ACL 2023},
37:   pages     = {8003--8017},
38:   year      = {2023},
39:   doi       = {10.18653/v1/2023.findings-acl.507},
40:   note      = {arXiv:2305.02301}
41: }
```

**Authoritative Metadata (Fetched 2026-10-15):**
- **Authoritative Title:** Distilling Step-by-Step! Outperforming Larger Language Models with Less Training Data and Smaller Model Sizes
- **Authoritative Authors (9 authors):** Cheng-Yu Hsieh, Chun-Liang Li, Chih-kuan Yeh, Hootan Nakhost, Yasuhisa Fujii, Alex Ratner, Ranjay Krishna, Chen-Yu Lee, Tomas Pfister
- **Authoritative Venue:** Findings of the Association for Computational Linguistics: ACL 2023, pages 8003-8017, DOI: 10.18653/v1/2023.findings-acl.507
- **Authoritative Year:** 2023
- **Authoritative URL:** https://doi.org/10.18653/v1/2023.findings-acl.507 (also ACL Anthology: https://aclanthology.org/2023.findings-acl.507/ and arXiv: https://arxiv.org/abs/2305.02301)
- **Formal Published Version Exists:** Yes (Findings of ACL 2023)
- **Bib Cites Formal Published Version:** Yes (bib cites Findings of the Association for Computational Linguistics: ACL 2023, pages 8003--8017, DOI 10.18653/v1/2023.findings-acl.507, year 2023)
- **Mismatches / Discrepancies Verbatim:**
  * None verbatim against ACL Anthology record (author names `Chih-kuan Yeh` and `Alex Ratner` match ACL Anthology exactly; bib appends note = {arXiv:2305.02301}).
- **Date of Fetch:** 2026-10-15

---

## 5. Entry `seal2025`

- **Bib Key:** `seal2025`
- **Bib File Locations:**
  * `/home/control/audit/fab376a/docs/paper/arxiv/refs.bib`: lines 43–52
  * `/home/control/audit/fab376a/docs/paper/bar/refs.bib`: lines 43–52
- **Cited in `docs/paper/arxiv`:** **Yes** (1 occurrence)
  * `fab376a/docs/paper/arxiv/sections/related_work.tex:11`: `on self-editing / self-adapting weights (e.g.\ SEAL~\citep{seal2025}) pushes the`
- **Cited in `docs/paper/bar`:** **Yes** (1 occurrence)
  * `fab376a/docs/paper/bar/main.tex:166`: `memory~\citep{titans2025, seal2025} push the parametric one. We do not claim primacy for`

**BibTeX Entry as Written:**
```bibtex
43: @inproceedings{seal2025,
44:   title     = {{Self-Adapting Language Models}},
45:   author    = {Zweiger, Adam and Pari, Jyothish and Guo, Han and Aky{\"u}rek, Ekin and Kim, Yoon and Agrawal, Pulkit},
46:   booktitle = {Advances in Neural Information Processing Systems (NeurIPS)},
47:   volume    = {38},
48:   pages     = {82334--82365},
49:   year      = {2025},
50:   doi       = {10.52202/085713-2483},
51:   note      = {arXiv:2506.10943}
52: }
```

**Authoritative Metadata (Fetched 2026-10-15):**
- **Authoritative Title:** Self-Adapting Language Models
- **Authoritative Authors (2 authors):** Crossref deposit (DOI 10.52202/085713-2483): 5 authors: Adam Zweiger, Jyo Pari, Han Guo, Yoon Kim, Pulkit Agrawal, arXiv abs (arXiv:2506.10943): 6 authors: Adam Zweiger, Jyothish Pari, Han Guo, Ekin Akyürek, Yoon Kim, Pulkit Agrawal
- **Authoritative Venue:** Advances in Neural Information Processing Systems 38 (2025), pages 82334-82365, DOI: 10.52202/085713-2483
- **Authoritative Year:** 2025
- **Authoritative URL:** https://doi.org/10.52202/085713-2483 (also arXiv: https://arxiv.org/abs/2506.10943)
- **Formal Published Version Exists:** Yes (Advances in Neural Information Processing Systems 38, 2025)
- **Bib Cites Formal Published Version:** Yes (bib cites NeurIPS 38, pages 82334--82365, DOI 10.52202/085713-2483, year 2025)
- **Mismatches / Discrepancies Verbatim:**
  * Author list discrepancy: Crossref metadata for DOI 10.52202/085713-2483 lists 5 authors (omits Ekin Akyürek, registers Jyothish Pari as `Jyo Pari`). The bib author field retains the 6 authors from arXiv (explicitly commented in lines 53-54 of refs.bib).
- **Date of Fetch:** 2026-10-15

---

## 6. Entry `awm2024`

- **Bib Key:** `awm2024`
- **Bib File Locations:**
  * `/home/control/audit/fab376a/docs/paper/arxiv/refs.bib`: lines 56–61
  * `/home/control/audit/fab376a/docs/paper/bar/refs.bib`: lines 56–61
- **Cited in `docs/paper/arxiv`:** **Yes** (2 occurrences)
  * `fab376a/docs/paper/arxiv/sections/discussion.tex:64`: `ExpeL~\citep{expel2024}, AWM~\citep{awm2024}; ASPIRE~\citep{lu2026aspire})`
  * `fab376a/docs/paper/arxiv/sections/related_work.tex:17`: `Agent-Workflow-Memory~\citep{awm2024} accumulate and reuse experience as external,`
- **Cited in `docs/paper/bar`:** **Yes** (1 occurrence)
  * `fab376a/docs/paper/bar/main.tex:157`: `Agent-memory systems~\citep{voyager2023, expel2024, awm2024} and`

**BibTeX Entry as Written:**
```bibtex
56: @article{awm2024,
57:   title   = {{Agent Workflow Memory}},
58:   author  = {Wang, Zora Zhiruo and Mao, Jiayuan and Fried, Daniel and Neubig, Graham},
59:   journal = {arXiv preprint arXiv:2409.07429},
60:   year    = {2024}
61: }
```

**Authoritative Metadata (Fetched 2026-10-15):**
- **Authoritative Title:** Agent Workflow Memory
- **Authoritative Authors (4 authors):** Zora Zhiruo Wang, Jiayuan Mao, Daniel Fried, Graham Neubig
- **Authoritative Venue:** Proceedings of the 42nd International Conference on Machine Learning (ICML 2025), PMLR volume 267, pages 63897-63911, 2025
- **Authoritative Year:** 2025
- **Authoritative URL:** https://proceedings.mlr.press/v267/wang25bx.html (also arXiv: https://arxiv.org/abs/2409.07429)
- **Formal Published Version Exists:** Yes (Proceedings of the 42nd International Conference on Machine Learning, PMLR volume 267, 2025)
- **Bib Cites Formal Published Version:** No (bib cites `arXiv preprint arXiv:2409.07429`, year 2024)
- **Mismatches / Discrepancies Verbatim:**
  * Venue: bib lists `journal = {arXiv preprint arXiv:2409.07429}`; authoritative published venue is `Proceedings of the 42nd International Conference on Machine Learning` (PMLR vol 267, pp. 63897–63911).
  * Year: bib lists `year = {2024}`; authoritative publication year is `2025`.
- **Date of Fetch:** 2026-10-15

---

## 7. Entry `tail2023`

- **Bib Key:** `tail2023`
- **Bib File Locations:**
  * `/home/control/audit/fab376a/docs/paper/arxiv/refs.bib`: lines 63–69
  * `/home/control/audit/fab376a/docs/paper/bar/refs.bib`: lines 63–69
- **Cited in `docs/paper/arxiv`:** **Yes** (1 occurrence)
  * `fab376a/docs/paper/arxiv/sections/related_work.tex:61`: `\paragraph{Lifelong / continual LoRA.} CORAL~\citep{luo2026coral}, TAIL~\citep{tail2023}, and related study adapter-%`
- **Cited in `docs/paper/bar`:** **No** (0 occurrences in `fab376a/docs/paper/bar/main.tex` and `acfd91d/docs/paper/bar/main.tex`)

**BibTeX Entry as Written:**
```bibtex
63: @inproceedings{tail2023,
64:   title     = {{TAIL: Task-specific Adapters for Imitation Learning with Large Pretrained Models}},
65:   author    = {Liu, Zuxin and Zhang, Jesse and Asadi, Kavosh and Liu, Yao and Zhao, Ding and Sabach, Shoham and Fakoor, Rasool},
66:   booktitle = {International Conference on Learning Representations (ICLR)},
67:   year      = {2024},
68:   note      = {arXiv:2310.05905}
69: }
```

**Authoritative Metadata (Fetched 2026-10-15):**
- **Authoritative Title:** TAIL: Task-specific Adapters for Imitation Learning with Large Pretrained Models
- **Authoritative Authors (7 authors):** Zuxin Liu, Jesse Zhang, Kavosh Asadi, Yao Liu, Ding Zhao, Shoham Sabach, Rasool Fakoor
- **Authoritative Venue:** International Conference on Learning Representations (ICLR 2024)
- **Authoritative Year:** 2024
- **Authoritative URL:** https://openreview.net/forum?id=RRayv1ZPN3 (also arXiv: https://arxiv.org/abs/2310.05905)
- **Formal Published Version Exists:** Yes (ICLR 2024)
- **Bib Cites Formal Published Version:** Yes (bib cites booktitle = {International Conference on Learning Representations (ICLR)}, year = {2024}, note = {arXiv:2310.05905})
- **Mismatches / Discrepancies Verbatim:**
  * Bib key naming: bib key is `tail2023`, whereas publication year is `2024`.
- **Date of Fetch:** 2026-10-15

---

## 8. Entry `simplevlarl2025`

- **Bib Key:** `simplevlarl2025`
- **Bib File Locations:**
  * `/home/control/audit/fab376a/docs/paper/arxiv/refs.bib`: lines 71–76
  * `/home/control/audit/fab376a/docs/paper/bar/refs.bib`: lines 71–76
- **Cited in `docs/paper/arxiv`:** **Yes** (1 occurrence)
  * `fab376a/docs/paper/arxiv/sections/related_work.tex:57`: `SimpleVLA-RL~\citep{simplevlarl2025} and related); our students are distilled+KTO-refined VLAs,`
- **Cited in `docs/paper/bar`:** **No** (0 occurrences in `fab376a/docs/paper/bar/main.tex` and `acfd91d/docs/paper/bar/main.tex`)

**BibTeX Entry as Written:**
```bibtex
71: @article{simplevlarl2025,
72:   title   = {{SimpleVLA-RL: Scaling VLA Training via Reinforcement Learning}},
73:   author  = {Li, Haozhan and Zuo, Yuxin and Yu, Jiale and Zhang, Yuhao and Yang, Zhaohui and Zhang, Kaiyan and Zhu, Xuekai and Zhang, Yuchen and Chen, Tianxing and Cui, Ganqu and Wang, Dehui and Luo, Dingxiang and Fan, Yuchen and Sun, Youbang and Zeng, Jia and Pang, Jiangmiao and Zhang, Shanghang and Wang, Yu and Mu, Yao and Zhou, Bowen and Ding, Ning},
74:   journal = {arXiv preprint arXiv:2509.09674},
75:   year    = {2025}
76: }
```

**Authoritative Metadata (Fetched 2026-10-15):**
- **Authoritative Title:** SimpleVLA-RL: Scaling VLA Training via Reinforcement Learning
- **Authoritative Authors (21 authors):** Haozhan Li, Yuxin Zuo, Jiale Yu, Yuhao Zhang, Zhaohui Yang, Kaiyan Zhang, Xuekai Zhu, Yuchen Zhang, Tianxing Chen, Ganqu Cui, Dehui Wang, Dingxiang Luo, Yuchen Fan, Youbang Sun, Jia Zeng, Jiangmiao Pang, Shanghang Zhang, Yu Wang, Yao Mu, Bowen Zhou, Ning Ding
- **Authoritative Venue:** arXiv preprint arXiv:2509.09674 (also ICLR 2026 conference submission on OpenReview)
- **Authoritative Year:** 2025 (arXiv) / 2026 (ICLR submission)
- **Authoritative URL:** https://arxiv.org/abs/2509.09674 (OpenReview: https://openreview.net/forum?id=TQhSodCM4r)
- **Formal Published Version Exists:** No (in review / conference submission at fetch date; preprint on arXiv)
- **Bib Cites Formal Published Version:** N/A (cites arXiv preprint)
- **Mismatches / Discrepancies Verbatim:**
  * None against arXiv record (title, 21 authors in exact order, year 2025 match).
- **Date of Fetch:** 2026-10-15

---

## 9. Entry `lora2021`

- **Bib Key:** `lora2021`
- **Bib File Locations:**
  * `/home/control/audit/fab376a/docs/paper/arxiv/refs.bib`: lines 80–85
  * `/home/control/audit/fab376a/docs/paper/bar/refs.bib`: lines 80–85
- **Cited in `docs/paper/arxiv`:** **Yes** (1 occurrence)
  * `fab376a/docs/paper/arxiv/sections/methods_d11.tex:42`: `Students are LoRA~\citep{lora2021} adapters (rank-16, $\alpha$=32, dropout 0.05) on the same`
- **Cited in `docs/paper/bar`:** **Yes** (1 occurrence)
  * `fab376a/docs/paper/bar/main.tex:102`: `task. From the \emph{same} trajectories we distil LoRA~\citep{lora2021}`

**BibTeX Entry as Written:**
```bibtex
80: @article{lora2021,
81:   title   = {{LoRA: Low-Rank Adaptation of Large Language Models}},
82:   author  = {Hu, Edward J. and Shen, Yelong and Wallis, Phillip and Allen-Zhu, Zeyuan and Li, Yuanzhi and Wang, Shean and Wang, Lu and Chen, Weizhu},
83:   journal = {arXiv preprint arXiv:2106.09685},
84:   year    = {2021}
85: }
```

**Authoritative Metadata (Fetched 2026-10-15):**
- **Authoritative Title:** LoRA: Low-Rank Adaptation of Large Language Models
- **Authoritative Authors (8 authors):** Edward J. Hu, Yelong Shen, Phillip Wallis, Zeyuan Allen-Zhu, Yuanzhi Li, Shean Wang, Lu Wang, Weizhu Chen
- **Authoritative Venue:** International Conference on Learning Representations (ICLR 2022)
- **Authoritative Year:** 2022
- **Authoritative URL:** https://openreview.net/forum?id=nZeVKeeFYf9 (also arXiv: https://arxiv.org/abs/2106.09685)
- **Formal Published Version Exists:** Yes (ICLR 2022)
- **Bib Cites Formal Published Version:** No (bib cites `arXiv preprint arXiv:2106.09685`, year 2021)
- **Mismatches / Discrepancies Verbatim:**
  * Venue: bib lists `journal = {arXiv preprint arXiv:2106.09685}`; authoritative published venue is `International Conference on Learning Representations (ICLR 2022)`.
  * Year: bib lists `year = {2021}`; authoritative publication year is `2022`.
- **Date of Fetch:** 2026-10-15

---

## 10. Entry `kto2024`

- **Bib Key:** `kto2024`
- **Bib File Locations:**
  * `/home/control/audit/fab376a/docs/paper/arxiv/refs.bib`: lines 87–93
  * `/home/control/audit/fab376a/docs/paper/bar/refs.bib`: lines 87–93
- **Cited in `docs/paper/arxiv`:** **Yes** (1 occurrence)
  * `fab376a/docs/paper/arxiv/sections/methods_d11.tex:47`: `progress-rounds, 1 epoch, lr 2e-4) followed by composable-KTO~\citep{kto2024} refinement`
- **Cited in `docs/paper/bar`:** **Yes** (1 occurrence)
  * `fab376a/docs/paper/bar/main.tex:103`: `student policies (SFT + composable-KTO~\citep{kto2024}) whose targets vary`

**BibTeX Entry as Written:**
```bibtex
87: @inproceedings{kto2024,
88:   title     = {{KTO: Model Alignment as Prospect Theoretic Optimization}},
89:   author    = {Ethayarajh, Kawin and Xu, Winnie and Muennighoff, Niklas and Jurafsky, Dan and Kiela, Douwe},
90:   booktitle = {International Conference on Machine Learning (ICML)},
91:   year      = {2024},
92:   note      = {arXiv:2402.01306}
93: }
```

**Authoritative Metadata (Fetched 2026-10-15):**
- **Authoritative Title:** Model Alignment as Prospect Theoretic Optimization (in formal PMLR proceedings); KTO: Model Alignment as Prospect Theoretic Optimization (on arXiv)
- **Authoritative Authors (5 authors):** Kawin Ethayarajh, Winnie Xu, Niklas Muennighoff, Dan Jurafsky, Douwe Kiela
- **Authoritative Venue:** Proceedings of the 41st International Conference on Machine Learning, PMLR volume 235, pages 12634-12651, 2024
- **Authoritative Year:** 2024
- **Authoritative URL:** https://proceedings.mlr.press/v235/ethayarajh24a.html (also arXiv: https://arxiv.org/abs/2402.01306)
- **Formal Published Version Exists:** Yes (ICML 2024 / PMLR volume 235)
- **Bib Cites Formal Published Version:** Yes (bib cites booktitle = {International Conference on Machine Learning (ICML)}, year = {2024}, note = {arXiv:2402.01306})
- **Mismatches / Discrepancies Verbatim:**
  * Title: bib includes `KTO:` prefix (`KTO: Model Alignment as Prospect Theoretic Optimization`); formal PMLR title omits `KTO:` (`Model Alignment as Prospect Theoretic Optimization`).
  * Volume and pages omitted: bib omits volume `235` and pages `12634--12651`.
- **Date of Fetch:** 2026-10-15

---

## 11. Entry `libero2023`

- **Bib Key:** `libero2023`
- **Bib File Locations:**
  * `/home/control/audit/fab376a/docs/paper/arxiv/refs.bib`: lines 95–104
  * `/home/control/audit/fab376a/docs/paper/bar/refs.bib`: lines 95–104
- **Cited in `docs/paper/arxiv`:** **Yes** (1 occurrence)
  * `fab376a/docs/paper/arxiv/sections/discussion.tex:147`: `interface to LIBERO~\citep{libero2023} and asking whether it clears the task before`
- **Cited in `docs/paper/bar`:** **No** (0 occurrences in `fab376a/docs/paper/bar/main.tex` and `acfd91d/docs/paper/bar/main.tex`)

**BibTeX Entry as Written:**
```bibtex
95: @inproceedings{libero2023,
96:   title     = {{LIBERO: Benchmarking Knowledge Transfer for Lifelong Robot Learning}},
97:   author    = {Liu, Bo and Zhu, Yifeng and Gao, Chongkai and Feng, Yihao and Liu, Qiang and Zhu, Yuke and Stone, Peter},
98:   booktitle = {Advances in Neural Information Processing Systems (NeurIPS)},
99:   volume    = {36},
100:   pages     = {44776--44791},
101:   year      = {2023},
102:   doi       = {10.52202/075280-1939},
103:   note      = {arXiv:2306.03310}
104: }
```

**Authoritative Metadata (Fetched 2026-10-15):**
- **Authoritative Title:** LIBERO: Benchmarking Knowledge Transfer for Lifelong Robot Learning
- **Authoritative Authors (7 authors):** Bo Liu, Yifeng Zhu, Chongkai Gao, Yihao Feng, Qiang Liu, Yuke Zhu, Peter Stone
- **Authoritative Venue:** Advances in Neural Information Processing Systems 36 (NeurIPS 2023), pages 44776-44791, DOI: 10.52202/075280-1939
- **Authoritative Year:** 2023
- **Authoritative URL:** https://doi.org/10.52202/075280-1939 (also arXiv: https://arxiv.org/abs/2306.03310)
- **Formal Published Version Exists:** Yes (Advances in Neural Information Processing Systems 36, 2023)
- **Bib Cites Formal Published Version:** Yes (bib cites Advances in Neural Information Processing Systems (NeurIPS), volume 36, pages 44776--44791, year 2023, DOI 10.52202/075280-1939, note = {arXiv:2306.03310})
- **Mismatches / Discrepancies Verbatim:**
  * None verbatim against Crossref metadata (bib appends note = {arXiv:2306.03310}).
- **Date of Fetch:** 2026-10-15

---

## 12. Entry `orbit2023`

- **Bib Key:** `orbit2023`
- **Bib File Locations:**
  * `/home/control/audit/fab376a/docs/paper/arxiv/refs.bib`: lines 106–112
  * `/home/control/audit/fab376a/docs/paper/bar/refs.bib`: lines 106–112
- **Cited in `docs/paper/arxiv`:** **Yes** (1 occurrence)
  * `fab376a/docs/paper/arxiv/sections/methods_d11.tex:14`: `Isaac Lab~\citep{orbit2023} bimanual manipulation rig with the right arm held frozen`
- **Cited in `docs/paper/bar`:** **No** (0 occurrences in `fab376a/docs/paper/bar/main.tex` and `acfd91d/docs/paper/bar/main.tex`)

**BibTeX Entry as Written:**
```bibtex
106: @article{orbit2023,
107:   title   = {{Orbit: A Unified Simulation Framework for Interactive Robot Learning Environments}},
108:   author  = {Mittal, Mayank and Yu, Calvin and Yu, Qinxi and Liu, Jingzhou and Rudin, Nikita and Hoeller, David and Yuan, Jia Lin and Singh, Ritvik and Guo, Yunrong and Mazhar, Hammad and Mandlekar, Ajay and Babich, Buck and State, Gavriel and Hutter, Marco and Garg, Animesh},
109:   journal = {IEEE Robotics and Automation Letters},
110:   year    = {2023},
111:   note    = {arXiv:2301.04195; NVIDIA Isaac Lab / Isaac Sim}
112: }
```

**Authoritative Metadata (Fetched 2026-10-15):**
- **Authoritative Title:** Orbit: A Unified Simulation Framework for Interactive Robot Learning Environments
- **Authoritative Authors (15 authors):** Mayank Mittal, Calvin Yu, Qinxi Yu, Jingzhou Liu, Nikita Rudin, David Hoeller, Jia Lin Yuan, Ritvik Singh, Yunrong Guo, Hammad Mazhar, Ajay Mandlekar, Buck Babich, Gavriel State, Marco Hutter, Animesh Garg
- **Authoritative Venue:** IEEE Robotics and Automation Letters, Volume 8, Issue 6, pages 3740-3747, June 2023, DOI: 10.1109/LRA.2023.3270034
- **Authoritative Year:** 2023
- **Authoritative URL:** https://doi.org/10.1109/lra.2023.3270034 (also arXiv: https://arxiv.org/abs/2301.04195)
- **Formal Published Version Exists:** Yes (IEEE Robotics and Automation Letters, June 2023)
- **Bib Cites Formal Published Version:** Yes (bib cites journal = {IEEE Robotics and Automation Letters}, year = {2023}, but omits volume, issue, pages, and DOI)
- **Mismatches / Discrepancies Verbatim:**
  * Volume, Issue, Pages, DOI omitted: bib omits volume `8`, issue `6`, pages `3740--3747`, and DOI `10.1109/LRA.2023.3270034`.
- **Date of Fetch:** 2026-10-15

---

## 13. Entry `dinov2_2023`

- **Bib Key:** `dinov2_2023`
- **Bib File Locations:**
  * `/home/control/audit/fab376a/docs/paper/arxiv/refs.bib`: lines 114–119
  * `/home/control/audit/fab376a/docs/paper/bar/refs.bib`: lines 114–119
- **Cited in `docs/paper/arxiv`:** **Yes** (1 occurrence)
  * `fab376a/docs/paper/arxiv/sections/methods_d11.tex:30`: `(DINOv2~\citep{dinov2_2023} image embedding, state-aware ranking) and`
- **Cited in `docs/paper/bar`:** **No** (0 occurrences in `fab376a/docs/paper/bar/main.tex` and `acfd91d/docs/paper/bar/main.tex`)

**BibTeX Entry as Written:**
```bibtex
114: @article{dinov2_2023,
115:   title   = {{DINOv2: Learning Robust Visual Features without Supervision}},
116:   author  = {Oquab, Maxime and Darcet, Timoth{\'e}e and Moutakanni, Th{\'e}o and Vo, Huy and Szafraniec, Marc and Khalidov, Vasil and Fernandez, Pierre and Haziza, Daniel and Massa, Francisco and El-Nouby, Alaaeldin and Assran, Mahmoud and Ballas, Nicolas and Galuba, Wojciech and Howes, Russell and Huang, Po-Yao and Li, Shang-Wen and Misra, Ishan and Rabbat, Michael and Sharma, Vasu and Synnaeve, Gabriel and Xu, Hu and Jegou, Herv{\'e} and Mairal, Julien and Labatut, Patrick and Joulin, Armand and Bojanowski, Piotr},
117:   journal = {arXiv preprint arXiv:2304.07193},
118:   year    = {2023}
119: }
```

**Authoritative Metadata (Fetched 2026-10-15):**
- **Authoritative Title:** DINOv2: Learning Robust Visual Features without Supervision
- **Authoritative Authors (26 authors):** Maxime Oquab, Timothée Darcet, Théo Moutakanni, Huy Vo, Marc Szafraniec, Vasil Khalidov, Pierre Fernandez, Daniel Haziza, Francisco Massa, Alaaeldin El-Nouby, Mahmoud Assran, Nicolas Ballas, Wojciech Galuba, Russell Howes, Po-Yao Huang, Shang-Wen Li, Ishan Misra, Michael Rabbat, Vasu Sharma, Gabriel Synnaeve, Hu Xu, Hervé Jegou, Julien Mairal, Patrick Labatut, Armand Joulin, Piotr Bojanowski
- **Authoritative Venue:** Transactions on Machine Learning Research (TMLR), accepted January 2024
- **Authoritative Year:** 2024
- **Authoritative URL:** https://openreview.net/forum?id=a68SUt6zFt (also arXiv: https://arxiv.org/abs/2304.07193)
- **Formal Published Version Exists:** Yes (Transactions on Machine Learning Research, 2024)
- **Bib Cites Formal Published Version:** No (bib cites `arXiv preprint arXiv:2304.07193`, year 2023)
- **Mismatches / Discrepancies Verbatim:**
  * Venue: bib lists `journal = {arXiv preprint arXiv:2304.07193}`; authoritative published venue is `Transactions on Machine Learning Research (TMLR)`.
  * Year: bib lists `year = {2023}`; authoritative formal publication year is `2024`.
- **Date of Fetch:** 2026-10-15

---

## 14. Entry `rag2020`

- **Bib Key:** `rag2020`
- **Bib File Locations:**
  * `/home/control/audit/fab376a/docs/paper/arxiv/refs.bib`: lines 121–127
  * `/home/control/audit/fab376a/docs/paper/bar/refs.bib`: lines 121–127
- **Cited in `docs/paper/arxiv`:** **Yes** (1 occurrence)
  * `fab376a/docs/paper/arxiv/sections/related_work.tex:6`: `it external and retrieving it (RAG~\citep{rag2020}), repeatedly finding`
- **Cited in `docs/paper/bar`:** **Yes** (2 occurrences)
  * `fab376a/docs/paper/bar/main.tex:108`: `retrieval-augmented pole in the sense of~\citet{rag2020}. The buffer is`
  * `fab376a/docs/paper/bar/main.tex:156`: `competitive or superior~\citep{rag2020, ovadia2024ft}.`

**BibTeX Entry as Written:**
```bibtex
121: @inproceedings{rag2020,
122:   title     = {{Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks}},
123:   author    = {Lewis, Patrick and Perez, Ethan and Piktus, Aleksandra and Petroni, Fabio and Karpukhin, Vladimir and Goyal, Naman and K{\"u}ttler, Heinrich and Lewis, Mike and Yih, Wen-tau and Rockt{\"a}schel, Tim and Riedel, Sebastian and Kiela, Douwe},
124:   booktitle = {Advances in Neural Information Processing Systems (NeurIPS)},
125:   year      = {2020},
126:   note      = {arXiv:2005.11401}
127: }
```

**Authoritative Metadata (Fetched 2026-10-15):**
- **Authoritative Title:** Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks
- **Authoritative Authors (12 authors):** Patrick Lewis, Ethan Perez, Aleksandra Piktus, Fabio Petroni, Vladimir Karpukhin, Naman Goyal, Heinrich Küttler, Mike Lewis, Wen-tau Yih, Tim Rocktäschel, Sebastian Riedel, Douwe Kiela
- **Authoritative Venue:** Advances in Neural Information Processing Systems 33 (NeurIPS 2020), pages 9459-9474, 2020
- **Authoritative Year:** 2020
- **Authoritative URL:** https://proceedings.neurips.cc/paper_files/paper/2020/hash/6b493230205f780e1bc26945df7481e5-Abstract.html (also arXiv: https://arxiv.org/abs/2005.11401)
- **Formal Published Version Exists:** Yes (NeurIPS 2020 / Advances in Neural Information Processing Systems 33)
- **Bib Cites Formal Published Version:** Yes (bib cites Advances in Neural Information Processing Systems (NeurIPS), year 2020, but omits volume and page numbers)
- **Mismatches / Discrepancies Verbatim:**
  * Volume and Pages omitted: bib omits volume `33` and pages `9459--9474`.
- **Date of Fetch:** 2026-10-15

---

## 15. Entry `embodiedcot2024`

- **Bib Key:** `embodiedcot2024`
- **Bib File Locations:**
  * `/home/control/audit/fab376a/docs/paper/arxiv/refs.bib`: lines 129–138
  * `/home/control/audit/fab376a/docs/paper/bar/refs.bib`: lines 129–138
- **Cited in `docs/paper/arxiv`:** **Yes** (1 occurrence)
  * `fab376a/docs/paper/arxiv/sections/related_work.tex:66`: `\paragraph{Reasoning distillation.} Distilling Step-by-Step~\citep{distillstepbystep2023}, Embodied-CoT~\citep{embodiedcot2024}, and`
- **Cited in `docs/paper/bar`:** **No** (0 occurrences in `fab376a/docs/paper/bar/main.tex` and `acfd91d/docs/paper/bar/main.tex`)

**BibTeX Entry as Written:**
```bibtex
129: @inproceedings{embodiedcot2024,
130:   title     = {{Robotic Control via Embodied Chain-of-Thought Reasoning}},
131:   author    = {Zawalski, Micha{\l} and Chen, William and Pertsch, Karl and Mees, Oier and Finn, Chelsea and Levine, Sergey},
132:   booktitle = {Proceedings of The 8th Conference on Robot Learning (CoRL)},
133:   series    = {Proceedings of Machine Learning Research},
134:   volume    = {270},
135:   pages     = {3157--3181},
136:   year      = {2025},
137:   note      = {arXiv:2407.08693}
138: }
```

**Authoritative Metadata (Fetched 2026-10-15):**
- **Authoritative Title:** Robotic Control via Embodied Chain-of-Thought Reasoning
- **Authoritative Authors (6 authors):** Michał Zawalski, William Chen, Karl Pertsch, Oier Mees, Chelsea Finn, Sergey Levine
- **Authoritative Venue:** Proceedings of The 8th Conference on Robot Learning, PMLR volume 270, pages 3157-3181, 2025
- **Authoritative Year:** 2025
- **Authoritative URL:** https://proceedings.mlr.press/v270/zawalski25a.html (also arXiv: https://arxiv.org/abs/2407.08693)
- **Formal Published Version Exists:** Yes (Proceedings of The 8th Conference on Robot Learning, PMLR 270, 2025)
- **Bib Cites Formal Published Version:** Yes (bib cites CoRL, series PMLR, volume 270, pages 3157--3181, year 2025)
- **Mismatches / Discrepancies Verbatim:**
  * None verbatim (booktitle appends `(CoRL)` acronym; note adds `arXiv:2407.08693`).
- **Date of Fetch:** 2026-10-15

---

## 16. Entry `gemma2024`

- **Bib Key:** `gemma2024`
- **Bib File Locations:**
  * `/home/control/audit/fab376a/docs/paper/arxiv/refs.bib`: lines 140–145
  * `/home/control/audit/fab376a/docs/paper/bar/refs.bib`: lines 140–145
- **Cited in `docs/paper/arxiv`:** **Yes** (1 occurrence)
  * `fab376a/docs/paper/arxiv/sections/methods_d11.tex:26`: `The teacher is Gemma-4-31B-it~\citep{gemma2024} (multimodal, 4-bit)`
- **Cited in `docs/paper/bar`:** **No** (0 occurrences in `fab376a/docs/paper/bar/main.tex` and `acfd91d/docs/paper/bar/main.tex`)

**BibTeX Entry as Written:**
```bibtex
140: @article{gemma2024,
141:   title   = {{Gemma: Open Models Based on Gemini Research and Technology}},
142:   author  = {{Gemma Team}},
143:   journal = {arXiv preprint arXiv:2403.08295},
144:   year    = {2024}
145: }
```

**Authoritative Metadata (Fetched 2026-10-15):**
- **Authoritative Title:** Gemma: Open Models Based on Gemini Research and Technology
- **Authoritative Authors:** Gemma Team (corporate author) followed by 108 individual co-authors on arXiv (first: Thomas Mesnard; last: Alek Andreev, Kathleen Kenealy, et al.; total 109 listed entries)
- **Authoritative Venue:** arXiv preprint arXiv:2403.08295
- **Authoritative Year:** 2024
- **Authoritative URL:** https://arxiv.org/abs/2403.08295
- **Formal Published Version Exists:** No (distributed as arXiv technical report / preprint)
- **Bib Cites Formal Published Version:** N/A (cites arXiv preprint)
- **Mismatches / Discrepancies Verbatim:**
  * Author format: bib lists corporate author `{Gemma Team}`; arXiv landing page lists `Gemma Team` followed by 108 named individual contributors.
- **Date of Fetch:** 2026-10-15

---

## 17. Entry `lu2026aspire`

- **Bib Key:** `lu2026aspire`
- **Bib File Locations:**
  * `/home/control/audit/fab376a/docs/paper/arxiv/refs.bib`: lines 152–161
  * `/home/control/audit/fab376a/docs/paper/bar/refs.bib`: lines 152–161
- **Cited in `docs/paper/arxiv`:** **Yes** (1 occurrence)
  * `fab376a/docs/paper/arxiv/sections/discussion.tex:64`: `ExpeL~\citep{expel2024}, AWM~\citep{awm2024}; ASPIRE~\citep{lu2026aspire})`
- **Cited in `docs/paper/bar`:** **No** (0 occurrences in `fab376a/docs/paper/bar/main.tex` and `acfd91d/docs/paper/bar/main.tex`)

**BibTeX Entry as Written:**
```bibtex
152: @article{lu2026aspire,
153:   title   = {{ASPIRE: Agentic Skills Discovery for Robotics}},
154:   author  = {Runyu Lu and Yubo Wu and Ethan Kou and Letian Fu and
155:              Wenli Xiao and Ajay Mandlekar and Yinzhen Xu and
156:              Guanya Shi and Ken Goldberg and Ang Chen and
157:              Mosharaf Chowdhury and Yuke Zhu and Linxi Fan and
158:              Guanzhi Wang},
159:   journal = {arXiv preprint arXiv:2607.00272},
160:   year    = {2026}
161: }
```

**Authoritative Metadata (Fetched 2026-10-15):**
- **Authoritative Title:** ASPIRE: Agentic /Skills Discovery for Robotics (on arXiv landing page)
- **Authoritative Authors (14 authors):** Runyu Lu, Yubo Wu, Ethan Kou, Letian Fu, Wenli Xiao, Ajay Mandlekar, Yinzhen Xu, Guanya Shi, Ken Goldberg, Ang Chen, Mosharaf Chowdhury, Yuke Zhu, Linxi "Jim" Fan, Guanzhi Wang
- **Authoritative Venue:** arXiv preprint arXiv:2607.00272
- **Authoritative Year:** 2026
- **Authoritative URL:** https://arxiv.org/abs/2607.00272
- **Formal Published Version Exists:** No (preprint on arXiv)
- **Bib Cites Formal Published Version:** N/A (cites arXiv preprint)
- **Mismatches / Discrepancies Verbatim:**
  * Title: arXiv metadata title has a stray slash: `ASPIRE: Agentic /Skills Discovery for Robotics`; bib has cleaned title `ASPIRE: Agentic Skills Discovery for Robotics` (editorial normalization noted in bib comment).
  * Author 13 name: arXiv lists `Linxi "Jim" Fan`; bib gives `Linxi Fan`.
- **Date of Fetch:** 2026-10-15

---

## 18. Entry `luo2026coral`

- **Bib Key:** `luo2026coral`
- **Bib File Locations:**
  * `/home/control/audit/fab376a/docs/paper/arxiv/refs.bib`: lines 166–171
  * `/home/control/audit/fab376a/docs/paper/bar/refs.bib`: lines 166–171
- **Cited in `docs/paper/arxiv`:** **Yes** (1 occurrence)
  * `fab376a/docs/paper/arxiv/sections/related_work.tex:61`: `\paragraph{Lifelong / continual LoRA.} CORAL~\citep{luo2026coral}, TAIL~\citep{tail2023}, and related study adapter-%`
- **Cited in `docs/paper/bar`:** **No** (0 occurrences in `fab376a/docs/paper/bar/main.tex` and `acfd91d/docs/paper/bar/main.tex`)

**BibTeX Entry as Written:**
```bibtex
166: @article{luo2026coral,
167:   title   = {{CORAL: Scalable Multi-Task Robot Learning via LoRA Experts}},
168:   author  = {Yuankai Luo and Woping Chen and Tong Liang and Zhenguo Li},
169:   journal = {arXiv preprint arXiv:2603.09298},
170:   year    = {2026}
171: }
```

**Authoritative Metadata (Fetched 2026-10-15):**
- **Authoritative Title:** CORAL: Scalable Multi-Task Robot Learning via LoRA Experts
- **Authoritative Authors (4 authors):** Yuankai Luo, Woping Chen, Tong Liang, Zhenguo Li
- **Authoritative Venue:** arXiv preprint arXiv:2603.09298
- **Authoritative Year:** 2026
- **Authoritative URL:** https://arxiv.org/abs/2603.09298
- **Formal Published Version Exists:** No (preprint on arXiv)
- **Bib Cites Formal Published Version:** N/A (cites arXiv preprint)
- **Mismatches / Discrepancies Verbatim:**
  * None (all fields match arXiv record verbatim).
- **Date of Fetch:** 2026-10-15

---

## 19. Entry `nosek2018preregistration`

- **Bib Key:** `nosek2018preregistration`
- **Bib File Locations:**
  * `/home/control/audit/fab376a/docs/paper/arxiv/refs.bib`: lines 173–183
  * `/home/control/audit/fab376a/docs/paper/bar/refs.bib`: lines 173–183
- **Cited in `docs/paper/arxiv`:** **Yes** (1 occurrence)
  * `fab376a/docs/paper/arxiv/sections/related_work.tex:73`: `\paragraph{Pre-registration in ML.} We adopt pre-registration~\citep{nosek2018preregistration,bertinetto2021prereg} as a methodological stance: registering hypotheses,`
- **Cited in `docs/paper/bar`:** **Yes** (1 occurrence)
  * `fab376a/docs/paper/bar/main.tex:115`: `stance~\citep{nosek2018preregistration,bertinetto2021prereg}: hypotheses,`

**BibTeX Entry as Written:**
```bibtex
173: @article{nosek2018preregistration,
174:   title   = {{The preregistration revolution}},
175:   author  = {Brian A. Nosek and Charles R. Ebersole and
176:              Alexander C. DeHaven and David T. Mellor},
177:   journal = {Proceedings of the National Academy of Sciences},
178:   volume  = {115},
179:   number  = {11},
180:   pages   = {2600--2606},
181:   year    = {2018},
182:   doi     = {10.1073/pnas.1708274114}
183: }
```

**Authoritative Metadata (Fetched 2026-10-15):**
- **Authoritative Title:** The preregistration revolution
- **Authoritative Authors (4 authors):** Brian A. Nosek, Charles R. Ebersole, Alexander C. DeHaven, David T. Mellor
- **Authoritative Venue:** Proceedings of the National Academy of Sciences, Volume 115, Number 11, pages 2600-2606, 2018, DOI: 10.1073/pnas.1708274114
- **Authoritative Year:** 2018
- **Authoritative URL:** https://doi.org/10.1073/pnas.1708274114
- **Formal Published Version Exists:** Yes (Proceedings of the National Academy of Sciences, 2018)
- **Bib Cites Formal Published Version:** Yes
- **Mismatches / Discrepancies Verbatim:**
  * None (all fields match verbatim).
- **Date of Fetch:** 2026-10-15

---

## 20. Entry `bertinetto2021prereg`

- **Bib Key:** `bertinetto2021prereg`
- **Bib File Locations:**
  * `/home/control/audit/fab376a/docs/paper/arxiv/refs.bib`: lines 185–192
  * `/home/control/audit/fab376a/docs/paper/bar/refs.bib`: lines 185–192
- **Cited in `docs/paper/arxiv`:** **Yes** (1 occurrence)
  * `fab376a/docs/paper/arxiv/sections/related_work.tex:73`: `\paragraph{Pre-registration in ML.} We adopt pre-registration~\citep{nosek2018preregistration,bertinetto2021prereg} as a methodological stance: registering hypotheses,`
- **Cited in `docs/paper/bar`:** **Yes** (1 occurrence)
  * `fab376a/docs/paper/bar/main.tex:115`: `stance~\citep{nosek2018preregistration,bertinetto2021prereg}: hypotheses,`

**BibTeX Entry as Written:**
```bibtex
185: @proceedings{bertinetto2021prereg,
186:   title     = {{NeurIPS 2020 Workshop on Pre-registration in Machine Learning}},
187:   editor    = {Luca Bertinetto and Jo{\~a}o F. Henriques and
188:                Samuel Albanie and Michela Paganini and G{\"u}l Varol},
189:   publisher = {PMLR},
190:   volume    = {148},
191:   year      = {2021}
192: }
```

**Authoritative Metadata (Fetched 2026-10-15):**
- **Authoritative Title:** NeurIPS 2020 Workshop on Pre-registration in Machine Learning
- **Authoritative Authors (5 authors):** Luca Bertinetto, João F. Henriques, Samuel Albanie, Michela Paganini, Gül Varol (Editors)
- **Authoritative Venue:** Proceedings of Machine Learning Research (PMLR volume 148), 2021
- **Authoritative Year:** 2021
- **Authoritative URL:** https://proceedings.mlr.press/v148/
- **Formal Published Version Exists:** Yes (Proceedings of Machine Learning Research, 2021)
- **Bib Cites Formal Published Version:** Yes
- **Mismatches / Discrepancies Verbatim:**
  * None (all fields match verbatim).
- **Date of Fetch:** 2026-10-15

---

## 21. Entry `mcclelland1995complementary`

- **Bib Key:** `mcclelland1995complementary`
- **Bib File Locations:**
  * `/home/control/audit/fab376a/docs/paper/arxiv/refs.bib`: lines 198–210
  * `/home/control/audit/fab376a/docs/paper/bar/refs.bib`: lines 198–210
- **Cited in `docs/paper/arxiv`:** **Yes** (1 occurrence)
  * `fab376a/docs/paper/arxiv/sections/discussion.tex:186`: `theory describes~\citep{mcclelland1995complementary, kumaran2016learning}.`
- **Cited in `docs/paper/bar`:** **Yes** (1 occurrence)
  * `fab376a/docs/paper/bar/main.tex:83`: `\citep{mcclelland1995complementary, kumaran2016learning}, yet skilled`

**BibTeX Entry as Written:**
```bibtex
198: @article{mcclelland1995complementary,
199:   title   = {Why there are complementary learning systems in the
200:              hippocampus and neocortex: insights from the successes
201:              and failures of connectionist models of learning and
202:              memory},
203:   author  = {James L. McClelland and Bruce L. McNaughton and
204:              Randall C. O'Reilly},
205:   journal = {Psychological Review},
206:   volume  = {102},
207:   number  = {3},
208:   pages   = {419--457},
209:   year    = {1995}
210: }
```

**Authoritative Metadata (Fetched 2026-10-15):**
- **Authoritative Title:** Why there are complementary learning systems in the hippocampus and neocortex: Insights from the successes and failures of connectionist models of learning and memory.
- **Authoritative Authors (3 authors):** James L. McClelland, Bruce L. McNaughton, Randall C. O'Reilly
- **Authoritative Venue:** Psychological Review, Volume 102, Issue 3, pages 419-457, 1995, DOI: 10.1037/0033-295X.102.3.419
- **Authoritative Year:** 1995
- **Authoritative URL:** https://doi.org/10.1037/0033-295x.102.3.419
- **Formal Published Version Exists:** Yes (Psychological Review, 1995)
- **Bib Cites Formal Published Version:** Yes
- **Mismatches / Discrepancies Verbatim:**
  * Bib omits DOI field `10.1037/0033-295X.102.3.419`.
- **Date of Fetch:** 2026-10-15

---

## 22. Entry `kumaran2016learning`

- **Bib Key:** `kumaran2016learning`
- **Bib File Locations:**
  * `/home/control/audit/fab376a/docs/paper/arxiv/refs.bib`: lines 212–222
  * `/home/control/audit/fab376a/docs/paper/bar/refs.bib`: lines 212–222
- **Cited in `docs/paper/arxiv`:** **Yes** (1 occurrence)
  * `fab376a/docs/paper/arxiv/sections/discussion.tex:186`: `theory describes~\citep{mcclelland1995complementary, kumaran2016learning}.`
- **Cited in `docs/paper/bar`:** **Yes** (1 occurrence)
  * `fab376a/docs/paper/bar/main.tex:83`: `\citep{mcclelland1995complementary, kumaran2016learning}, yet skilled`

**BibTeX Entry as Written:**
```bibtex
212: @article{kumaran2016learning,
213:   title   = {What learning systems do intelligent agents need?
214:              Complementary learning systems theory updated},
215:   author  = {Dharshan Kumaran and Demis Hassabis and
216:              James L. McClelland},
217:   journal = {Trends in Cognitive Sciences},
218:   volume  = {20},
219:   number  = {7},
220:   pages   = {512--534},
221:   year    = {2016}
222: }
```

**Authoritative Metadata (Fetched 2026-10-15):**
- **Authoritative Title:** What Learning Systems do Intelligent Agents Need? Complementary Learning Systems Theory Updated
- **Authoritative Authors (3 authors):** Dharshan Kumaran, Demis Hassabis, James L. McClelland
- **Authoritative Venue:** Trends in Cognitive Sciences, Volume 20, Issue 7, pages 512-534, 2016, DOI: 10.1016/j.tics.2016.05.004
- **Authoritative Year:** 2016
- **Authoritative URL:** https://doi.org/10.1016/j.tics.2016.05.004
- **Formal Published Version Exists:** Yes (Trends in Cognitive Sciences, 2016)
- **Bib Cites Formal Published Version:** Yes
- **Mismatches / Discrepancies Verbatim:**
  * Bib omits DOI field `10.1016/j.tics.2016.05.004`.
- **Date of Fetch:** 2026-10-15

---

## 23. Entry `ovadia2024ft`

- **Bib Key:** `ovadia2024ft`
- **Bib File Locations:**
  * `/home/control/audit/fab376a/docs/paper/arxiv/refs.bib`: lines 227–233
  * `/home/control/audit/fab376a/docs/paper/bar/refs.bib`: lines 227–233
- **Cited in `docs/paper/arxiv`:** **No** (0 occurrences in `fab376a/docs/paper/arxiv/*.tex` and `acfd91d/docs/paper/arxiv/*.tex`)
- **Cited in `docs/paper/bar`:** **Yes** (1 occurrence)
  * `fab376a/docs/paper/bar/main.tex:156`: `competitive or superior~\citep{rag2020, ovadia2024ft}.`

**BibTeX Entry as Written:**
```bibtex
227: @inproceedings{ovadia2024ft,
228:   title     = {{Fine-Tuning or Retrieval? Comparing Knowledge Injection in LLMs}},
229:   author    = {Ovadia, Oded and Brief, Menachem and Mishaeli, Moshik and Elisha, Oren},
230:   booktitle = {Proceedings of the 2024 Conference on Empirical Methods in Natural Language Processing (EMNLP)},
231:   year      = {2024},
232:   note      = {arXiv:2312.05934}
233: }
```

**Authoritative Metadata (Fetched 2026-10-15):**
- **Authoritative Title:** Fine-Tuning or Retrieval? Comparing Knowledge Injection in LLMs
- **Authoritative Authors (4 authors):** Oded Ovadia, Menachem Brief, Moshik Mishaeli, Oren Elisha
- **Authoritative Venue:** Proceedings of the 2024 Conference on Empirical Methods in Natural Language Processing (EMNLP 2024), pages 237-250, 2024, DOI: 10.18653/v1/2024.emnlp-main.15
- **Authoritative Year:** 2024
- **Authoritative URL:** https://doi.org/10.18653/v1/2024.emnlp-main.15 (also ACL Anthology: https://aclanthology.org/2024.emnlp-main.15/ and arXiv: https://arxiv.org/abs/2312.05934)
- **Formal Published Version Exists:** Yes (EMNLP 2024 proceedings)
- **Bib Cites Formal Published Version:** Yes (bib cites EMNLP 2024 proceedings, but omits pages and DOI; note adds arXiv:2312.05934)
- **Mismatches / Discrepancies Verbatim:**
  * Pages and DOI omitted: bib omits pages `237--250` and DOI `10.18653/v1/2024.emnlp-main.15`.
  * Citation document disparity: CITED in `bar/main.tex:156`, but UNCITED in `arxiv` document.
- **Date of Fetch:** 2026-10-15

---

## 24. Entry `zhu2024raea`

- **Bib Key:** `zhu2024raea`
- **Bib File Locations:**
  * `/home/control/audit/fab376a/docs/paper/arxiv/refs.bib`: lines 235–241
  * `/home/control/audit/fab376a/docs/paper/bar/refs.bib`: lines 235–241
- **Cited in `docs/paper/arxiv`:** **Yes** (1 occurrence)
  * `fab376a/docs/paper/arxiv/sections/related_work.tex:42`: `STRAP~\citep{memmel2024strap} / RAEA~\citep{zhu2024raea} retrieve`
- **Cited in `docs/paper/bar`:** **Yes** (1 occurrence)
  * `fab376a/docs/paper/bar/main.tex:158`: `retrieval-augmented embodied policies and VLAs~\citep{zhu2024raea,`

**BibTeX Entry as Written:**
```bibtex
235: @inproceedings{zhu2024raea,
236:   title     = {{Retrieval-Augmented Embodied Agents}},
237:   author    = {Zhu, Yichen and Ou, Zhicai and Mou, Xiaofeng and Tang, Jian},
238:   booktitle = {Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition (CVPR)},
239:   pages     = {17985--17995},
240:   year      = {2024}
241: }
```

**Authoritative Metadata (Fetched 2026-10-15):**
- **Authoritative Title:** Retrieval-Augmented Embodied Agents
- **Authoritative Authors (4 authors):** Yichen Zhu, Zhicai Ou, Xiaofeng Mou, Jian Tang
- **Authoritative Venue:** Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition (CVPR 2024), pages 17985-17995, 2024, DOI: 10.1109/cvpr52733.2024.01703
- **Authoritative Year:** 2024
- **Authoritative URL:** https://doi.org/10.1109/cvpr52733.2024.01703
- **Formal Published Version Exists:** Yes (CVPR 2024 proceedings)
- **Bib Cites Formal Published Version:** Yes (cites CVPR 2024, pages 17985--17995)
- **Mismatches / Discrepancies Verbatim:**
  * Bib omits DOI field `10.1109/cvpr52733.2024.01703`.
- **Date of Fetch:** 2026-10-15

---

## 25. Entry `memmel2024strap`

- **Bib Key:** `memmel2024strap`
- **Bib File Locations:**
  * `/home/control/audit/fab376a/docs/paper/arxiv/refs.bib`: lines 243–248
  * `/home/control/audit/fab376a/docs/paper/bar/refs.bib`: lines 243–248
- **Cited in `docs/paper/arxiv`:** **Yes** (1 occurrence)
  * `fab376a/docs/paper/arxiv/sections/related_work.tex:42`: `STRAP~\citep{memmel2024strap} / RAEA~\citep{zhu2024raea} retrieve`
- **Cited in `docs/paper/bar`:** **Yes** (1 occurrence)
  * `fab376a/docs/paper/bar/main.tex:159`: `memmel2024strap, expresvla2025, retrievethensteer2026} occupy the`

**BibTeX Entry as Written:**
```bibtex
243: @article{memmel2024strap,
244:   title   = {{STRAP: Robot Sub-Trajectory Retrieval for Augmented Policy Learning}},
245:   author  = {Memmel, Marius and Berg, Jacob and Chen, Bingqing and Gupta, Abhishek and Francis, Jonathan},
246:   journal = {arXiv preprint arXiv:2412.15182},
247:   year    = {2024}
248: }
```

**Authoritative Metadata (Fetched 2026-10-15):**
- **Authoritative Title:** STRAP: Robot Sub-Trajectory Retrieval for Augmented Policy Learning
- **Authoritative Authors (5 authors):** Marius Memmel, Jacob Berg, Bingqing Chen, Abhishek Gupta, Jonathan Francis
- **Authoritative Venue:** International Conference on Learning Representations (ICLR 2025)
- **Authoritative Year:** 2025
- **Authoritative URL:** https://openreview.net/forum?id=4VHiptx7xe (also arXiv: https://arxiv.org/abs/2412.15182)
- **Formal Published Version Exists:** Yes (ICLR 2025)
- **Bib Cites Formal Published Version:** No (bib cites `arXiv preprint arXiv:2412.15182`, year 2024)
- **Mismatches / Discrepancies Verbatim:**
  * Venue: bib lists `journal = {arXiv preprint arXiv:2412.15182}`; authoritative published venue is `International Conference on Learning Representations (ICLR 2025)`.
  * Year: bib lists `year = {2024}`; authoritative publication year is `2025`.
- **Date of Fetch:** 2026-10-15

---

## 26. Entry `pistar06_2025`

- **Bib Key:** `pistar06_2025`
- **Bib File Locations:**
  * `/home/control/audit/fab376a/docs/paper/arxiv/refs.bib`: lines 257–263
  * `/home/control/audit/fab376a/docs/paper/bar/refs.bib`: lines 257–263
- **Cited in `docs/paper/arxiv`:** **Yes** (1 occurrence)
  * `fab376a/docs/paper/arxiv/sections/related_work.tex:49`: `Others fold experience \emph{into weights}: RECAP / $\pi^{*}_{0.6}$~\citep{pistar06_2025}`
- **Cited in `docs/paper/bar`:** **Yes** (1 occurrence)
  * `fab376a/docs/paper/bar/main.tex:164`: `post-training~\citep{pistar06_2025}, distilling retrieved experience into`

**BibTeX Entry as Written:**
```bibtex
257: @article{pistar06_2025,
258:   title   = {{$\pi^{*}_{0.6}$: a {VLA} That Learns From Experience}},
259:   author  = {{Physical Intelligence} and Amin, Ali and Aniceto, Raichelle and Balakrishna, Ashwin and Black, Kevin and others},
260:   journal = {arXiv preprint arXiv:2511.14759},
261:   year    = {2025},
262:   note    = {RECAP: RL with Experience and Corrections via Advantage-conditioned Policies}
263: }
```

**Authoritative Metadata (Fetched 2026-10-15):**
- **Authoritative Title:** $\pi^{*}_{0.6}$: a VLA That Learns From Experience
- **Authoritative Authors (13 authors):** Physical Intelligence (corporate author), Ali Amin, Raichelle Aniceto, Ashwin Balakrishna, Kevin Black, Ken Conley, Grace Connors, James Darpinian, Karan Dhabalia, Jared DiCarlo, Lili Yu, Ury Zhilinsky, Zhiyuan Zhou (and 43 additional authors; total 56 listed on arXiv)
- **Authoritative Venue:** arXiv preprint arXiv:2511.14759
- **Authoritative Year:** 2025
- **Authoritative URL:** https://arxiv.org/abs/2511.14759
- **Formal Published Version Exists:** No (preprint on arXiv)
- **Bib Cites Formal Published Version:** N/A (cites arXiv preprint)
- **Mismatches / Discrepancies Verbatim:**
  * Author list truncated: bib lists `{Physical Intelligence}` and 4 named authors followed by `others`; arXiv landing page lists 56 authors in total.
- **Date of Fetch:** 2026-10-15

---

## 27. Entry `expresvla2025`

- **Bib Key:** `expresvla2025`
- **Bib File Locations:**
  * `/home/control/audit/fab376a/docs/paper/arxiv/refs.bib`: lines 265–271
  * `/home/control/audit/fab376a/docs/paper/bar/refs.bib`: lines 265–271
- **Cited in `docs/paper/arxiv`:** **Yes** (1 occurrence)
  * `fab376a/docs/paper/arxiv/sections/related_work.tex:39`: `retrieved}: ExpReS-VLA~\citep{expresvla2025} specialises VLAs through`
- **Cited in `docs/paper/bar`:** **Yes** (1 occurrence)
  * `fab376a/docs/paper/bar/main.tex:159`: `memmel2024strap, expresvla2025, retrievethensteer2026} occupy the`

**BibTeX Entry as Written:**
```bibtex
265: @inproceedings{expresvla2025,
266:   title     = {{ExpReS-VLA: Specializing Vision-Language-Action Models Through Experience Replay and Retrieval}},
267:   author    = {Syed, Shahram Najam and Ahuja, Yatharth and Jakobsson, Arthur and Ichnowski, Jeff},
268:   booktitle = {IEEE International Conference on Robotics and Automation (ICRA)},
269:   year      = {2026},
270:   note      = {arXiv:2511.06202}
271: }
```

**Authoritative Metadata (Fetched 2026-10-15):**
- **Authoritative Title:** ExpReS-VLA: Specializing Vision-Language-Action Models Through Experience Replay and Retrieval
- **Authoritative Authors (4 authors):** Shahram Najam Syed, Yatharth Ahuja, Arthur Jakobsson, Jeff Ichnowski
- **Authoritative Venue:** IEEE International Conference on Robotics and Automation (ICRA 2026)
- **Authoritative Year:** 2026
- **Authoritative URL:** https://arxiv.org/abs/2511.06202
- **Formal Published Version Exists:** Yes (accepted to ICRA 2026)
- **Bib Cites Formal Published Version:** Yes (cites ICRA 2026, note records arXiv:2511.06202)
- **Mismatches / Discrepancies Verbatim:**
  * None (venue and year match acceptance; conference proceedings page numbers not yet assigned at fetch date).
- **Date of Fetch:** 2026-10-15

---

## 28. Entry `retrievethensteer2026`

- **Bib Key:** `retrievethensteer2026`
- **Bib File Locations:**
  * `/home/control/audit/fab376a/docs/paper/arxiv/refs.bib`: lines 273–278
  * `/home/control/audit/fab376a/docs/paper/bar/refs.bib`: lines 273–278
- **Cited in `docs/paper/arxiv`:** **Yes** (1 occurrence)
  * `fab376a/docs/paper/arxiv/sections/related_work.tex:40`: `experience replay and retrieval, Retrieve-then-Steer~\citep{retrievethensteer2026}`
- **Cited in `docs/paper/bar`:** **Yes** (1 occurrence)
  * `fab376a/docs/paper/bar/main.tex:159`: `memmel2024strap, expresvla2025, retrievethensteer2026} occupy the`

**BibTeX Entry as Written:**
```bibtex
273: @article{retrievethensteer2026,
274:   title   = {{Retrieve-then-Steer: Online Success Memory for Test-Time Adaptation of Generative VLAs}},
275:   author  = {Zhao, Jianchao and Yang, Huoren and Hu, Yusong and Gao, Yuyang and Ou, Qiguan and Wan, Cong and Dong, SongLin and Ma, Zhiheng and Gong, Yihong},
276:   journal = {arXiv preprint arXiv:2605.10094},
277:   year    = {2026}
278: }
```

**Authoritative Metadata (Fetched 2026-10-15):**
- **Authoritative Title:** Retrieve-then-Steer: Online Success Memory for Test-Time Adaptation of Generative VLAs
- **Authoritative Authors (9 authors):** Jianchao Zhao, Huoren Yang, Yusong Hu, Yuyang Gao, Qiguan Ou, Cong Wan, SongLin Dong, Zhiheng Ma, Yihong Gong
- **Authoritative Venue:** arXiv preprint arXiv:2605.10094
- **Authoritative Year:** 2026
- **Authoritative URL:** https://arxiv.org/abs/2605.10094
- **Formal Published Version Exists:** No (preprint on arXiv)
- **Bib Cites Formal Published Version:** N/A (cites arXiv preprint)
- **Mismatches / Discrepancies Verbatim:**
  * None (all fields match arXiv record verbatim).
- **Date of Fetch:** 2026-10-15

---

## 29. Entry `memoryvla2025`

- **Bib Key:** `memoryvla2025`
- **Bib File Locations:**
  * `/home/control/audit/fab376a/docs/paper/arxiv/refs.bib`: lines 281–287
  * `/home/control/audit/fab376a/docs/paper/bar/refs.bib`: lines 281–287
- **Cited in `docs/paper/arxiv`:** **Yes** (1 occurrence)
  * `fab376a/docs/paper/arxiv/sections/related_work.tex:43`: `sub-trajectories or augment embodied agents; MemoryVLA~\citep{memoryvla2025}`
- **Cited in `docs/paper/bar`:** **No** (0 occurrences in `fab376a/docs/paper/bar/main.tex` and `acfd91d/docs/paper/bar/main.tex`)

**BibTeX Entry as Written:**
```bibtex
281: @inproceedings{memoryvla2025,
282:   title     = {{MemoryVLA: Perceptual-Cognitive Memory in Vision-Language-Action Models for Robotic Manipulation}},
283:   author    = {Shi, Hao and Xie, Bin and Liu, Yingfei and Sun, Lin and Liu, Fengrong and Wang, Tiancai and Zhou, Erjin and Fan, Haoqiang and Zhang, Xiangyu and Huang, Gao},
284:   booktitle = {International Conference on Learning Representations (ICLR)},
285:   year      = {2026},
286:   note      = {arXiv:2508.19236}
287: }
```

**Authoritative Metadata (Fetched 2026-10-15):**
- **Authoritative Title:** MemoryVLA: Perceptual-Cognitive Memory in Vision-Language-Action Models for Robotic Manipulation
- **Authoritative Authors (10 authors):** Hao Shi, Bin Xie, Yingfei Liu, Lin Sun, Fengrong Liu, Tiancai Wang, Erjin Zhou, Haoqiang Fan, Xiangyu Zhang, Gao Huang
- **Authoritative Venue:** International Conference on Learning Representations (ICLR 2026)
- **Authoritative Year:** 2026
- **Authoritative URL:** https://openreview.net/forum?id=54U3XHf7qq (also arXiv: https://arxiv.org/abs/2508.19236)
- **Formal Published Version Exists:** Yes (ICLR 2026)
- **Bib Cites Formal Published Version:** Yes (cites ICLR 2026, note records arXiv:2508.19236)
- **Mismatches / Discrepancies Verbatim:**
  * None (venue and year match ICLR 2026; bib key has 2025 reflecting preprint date).
- **Date of Fetch:** 2026-10-15

---

## 30. Entry `robomme2026`

- **Bib Key:** `robomme2026`
- **Bib File Locations:**
  * `/home/control/audit/fab376a/docs/paper/arxiv/refs.bib`: lines 289–295
  * `/home/control/audit/fab376a/docs/paper/bar/refs.bib`: lines 289–295
- **Cited in `docs/paper/arxiv`:** **Yes** (1 occurrence)
  * `fab376a/docs/paper/arxiv/sections/related_work.tex:45`: `RoboMME~\citep{robomme2026} benchmarks memory for generalist policies;`
- **Cited in `docs/paper/bar`:** **No** (0 occurrences in `fab376a/docs/paper/bar/main.tex` and `acfd91d/docs/paper/bar/main.tex`)

**BibTeX Entry as Written:**
```bibtex
289: @inproceedings{robomme2026,
290:   title     = {{RoboMME: Benchmarking and Understanding Memory for Robotic Generalist Policies}},
291:   author    = {Dai, Yinpei and Fu, Hongze and Lee, Jayjun and Liu, Yuejiang and Zhang, Haoran and Yang, Jianing and Finn, Chelsea and Fazeli, Nima and Chai, Joyce},
292:   booktitle = {International Conference on Machine Learning (ICML)},
293:   year      = {2026},
294:   note      = {arXiv:2603.04639}
295: }
```

**Authoritative Metadata (Fetched 2026-10-15):**
- **Authoritative Title:** RoboMME: Benchmarking and Understanding Memory for Robotic Generalist Policies
- **Authoritative Authors (9 authors):** Yinpei Dai, Hongze Fu, Jayjun Lee, Yuejiang Liu, Haoran Zhang, Jianing Yang, Chelsea Finn, Nima Fazeli, Joyce Chai
- **Authoritative Venue:** International Conference on Machine Learning (ICML 2026)
- **Authoritative Year:** 2026
- **Authoritative URL:** https://arxiv.org/abs/2603.04639
- **Formal Published Version Exists:** Yes (ICML 2026)
- **Bib Cites Formal Published Version:** Yes (cites ICML 2026, note records arXiv:2603.04639)
- **Mismatches / Discrepancies Verbatim:**
  * None against ICML 2026 acceptance metadata.
- **Date of Fetch:** 2026-10-15

---

## 31. Entry `tmem2026`

- **Bib Key:** `tmem2026`
- **Bib File Locations:**
  * `/home/control/audit/fab376a/docs/paper/arxiv/refs.bib`: lines 297–303
  * `/home/control/audit/fab376a/docs/paper/bar/refs.bib`: lines 297–303
- **Cited in `docs/paper/arxiv`:** **Yes** (1 occurrence)
  * `fab376a/docs/paper/arxiv/sections/discussion.tex:78`: `and parametric self-evolution (TMEM~\citep{tmem2026}) are precisely`
- **Cited in `docs/paper/bar`:** **No** (0 occurrences in `fab376a/docs/paper/bar/main.tex` and `acfd91d/docs/paper/bar/main.tex`)

**BibTeX Entry as Written:**
```bibtex
297: @article{tmem2026,
298:   title   = {{Scaling Self-Evolving Agents via Parametric Memory}},
299:   author  = {Ren, Tao and Luo, Weiyao and Yang, Hui and Zhu, Rongzhi and Huang, Xiang and Wu, Yuchuan and Chou, Bingxue and Ye, Jieping and Liang, Jiafeng and Li, Yongbin and Peng, Yijie},
300:   journal = {arXiv preprint arXiv:2606.04536},
301:   year    = {2026},
302:   note    = {introduces the TMEM framework}
303: }
```

**Authoritative Metadata (Fetched 2026-10-15):**
- **Authoritative Title:** Scaling Self-Evolving Agents via Parametric Memory
- **Authoritative Authors (11 authors):** Tao Ren, Weiyao Luo, Hui Yang, Rongzhi Zhu, Xiang Huang, Yuchuan Wu, Bingxue Chou, Jieping Ye, Jiafeng Liang, Yongbin Li, Yijie Peng
- **Authoritative Venue:** arXiv preprint arXiv:2606.04536
- **Authoritative Year:** 2026
- **Authoritative URL:** https://arxiv.org/abs/2606.04536
- **Formal Published Version Exists:** No (preprint on arXiv)
- **Bib Cites Formal Published Version:** N/A (cites arXiv preprint)
- **Mismatches / Discrepancies Verbatim:**
  * None (all fields match arXiv record; bib note adds explanatory note about TMEM framework).
- **Date of Fetch:** 2026-10-15

---

## 32. Entry `memharness2026`

- **Bib Key:** `memharness2026`
- **Bib File Locations:**
  * `/home/control/audit/fab376a/docs/paper/arxiv/refs.bib`: lines 305–310
  * `/home/control/audit/fab376a/docs/paper/bar/refs.bib`: lines 305–310
- **Cited in `docs/paper/arxiv`:** **Yes** (1 occurrence)
  * `fab376a/docs/paper/arxiv/sections/discussion.tex:81`: `\S4.3 shows our recipe drops. MemHarness~\citep{memharness2026} makes the`
- **Cited in `docs/paper/bar`:** **No** (0 occurrences in `fab376a/docs/paper/bar/main.tex` and `acfd91d/docs/paper/bar/main.tex`)

**BibTeX Entry as Written:**
```bibtex
305: @article{memharness2026,
306:   title   = {{MemHarness: Memory Is Reconstructed, Not Replayed}},
307:   author  = {Wu, Rong and Fu, Daocheng and Wen, Licheng and Yang, Xuemeng and Zou, Shu and Mei, Jianbiao and Wang, Yuxin and Zhang, Hairong and Yang, Yu and Hu, Tao and Zhang, Cong and Shi, Botian and Cai, Pinlong},
308:   journal = {arXiv preprint arXiv:2607.28272},
309:   year    = {2026}
310: }
```

**Authoritative Metadata (Fetched 2026-10-15):**
- **Authoritative Title:** MemHarness: Memory Is Reconstructed, Not Replayed
- **Authoritative Authors (13 authors):** Rong Wu, Daocheng Fu, Licheng Wen, Xuemeng Yang, Shu Zou, Jianbiao Mei, Yuxin Wang, Hairong Zhang, Yu Yang, Tao Hu, Cong Zhang, Botian Shi, Pinlong Cai
- **Authoritative Venue:** arXiv preprint arXiv:2607.28272
- **Authoritative Year:** 2026
- **Authoritative URL:** https://arxiv.org/abs/2607.28272
- **Formal Published Version Exists:** No (preprint on arXiv)
- **Bib Cites Formal Published Version:** N/A (cites arXiv preprint)
- **Mismatches / Discrepancies Verbatim:**
  * None (all fields match arXiv record verbatim).
- **Date of Fetch:** 2026-10-15

---

## 33. Entry `clift2026`

- **Bib Key:** `clift2026`
- **Bib File Locations:**
  * `/home/control/audit/fab376a/docs/paper/arxiv/refs.bib`: lines 312–317
  * `/home/control/audit/fab376a/docs/paper/bar/refs.bib`: lines 312–317
- **Cited in `docs/paper/arxiv`:** **Yes** (1 occurrence)
  * `fab376a/docs/paper/arxiv/sections/discussion.tex:126`: `closed-loop iterative fine-tuning (CLIFT~\citep{clift2026}) and`
- **Cited in `docs/paper/bar`:** **No** (0 occurrences in `fab376a/docs/paper/bar/main.tex` and `acfd91d/docs/paper/bar/main.tex`)

**BibTeX Entry as Written:**
```bibtex
312: @article{clift2026,
313:   title   = {{CLIFT: Turning Gemini Robotics On-Device into Humanoid Specialists via Non-Invasive Closed-Loop Iterative Fine-Tuning}},
314:   author  = {Chen, Yuxin and Srikanth, Hari and Jew, Nathan and Wu, Menglin and Wang, Pengcheng and Ren, Junli and Tomizuka, Masayoshi and Xu, Peng and Xie, Jinyu and Tian, Thomas},
315:   journal = {arXiv preprint arXiv:2607.29172},
316:   year    = {2026}
317: }
```

**Authoritative Metadata (Fetched 2026-10-15):**
- **Authoritative Title:** CLIFT: Turning Gemini Robotics On-Device into Humanoid Specialists via Non-Invasive Closed-Loop Iterative Fine-Tuning
- **Authoritative Authors (10 authors):** Yuxin Chen, Hari Srikanth, Nathan Jew, Menglin Wu, Pengcheng Wang, Junli Ren, Masayoshi Tomizuka, Peng Xu, Jinyu Xie, Thomas Tian
- **Authoritative Venue:** arXiv preprint arXiv:2607.29172
- **Authoritative Year:** 2026
- **Authoritative URL:** https://arxiv.org/abs/2607.29172
- **Formal Published Version Exists:** No (preprint on arXiv)
- **Bib Cites Formal Published Version:** N/A (cites arXiv preprint)
- **Mismatches / Discrepancies Verbatim:**
  * None (all fields match arXiv record verbatim).
- **Date of Fetch:** 2026-10-15

---

## 34. Entry `routing2026`

- **Bib Key:** `routing2026`
- **Bib File Locations:**
  * `/home/control/audit/fab376a/docs/paper/arxiv/refs.bib`: lines 321–326
  * `/home/control/audit/fab376a/docs/paper/bar/refs.bib`: lines 321–326
- **Cited in `docs/paper/arxiv`:** **Yes** (2 occurrences)
  * `fab376a/docs/paper/arxiv/sections/discussion.tex:118`: `apparently opposite finding of \citet{routing2026}, where lessons did better`
  * `fab376a/docs/paper/arxiv/sections/related_work.tex:26`: `\citet{routing2026} compare fine-tuning and prompt retrieval on the`
- **Cited in `docs/paper/bar`:** **Yes** (1 occurrence)
  * `fab376a/docs/paper/bar/main.tex:162`: `weights~\citep{routing2026}. Behaviour and context`

**BibTeX Entry as Written:**
```bibtex
321: @article{routing2026,
322:   title   = {{Not All Experience Belongs in the Weights: Component Routing for Self-Improving GUI Agents}},
323:   author  = {Wu, Beining and Ding, Zihao and Huang, Jun},
324:   journal = {arXiv preprint arXiv:2610.01787},
325:   year    = {2026}
326: }
```

**Authoritative Metadata (Fetched 2026-10-15):**
- **Authoritative Title:** Not All Experience Belongs in the Weights: Component Routing for Self-Improving GUI Agents
- **Authoritative Authors (3 authors):** Beining Wu, Zihao Ding, Jun Huang
- **Authoritative Venue:** arXiv preprint arXiv:2610.01787
- **Authoritative Year:** 2026
- **Authoritative URL:** https://arxiv.org/abs/2610.01787
- **Formal Published Version Exists:** No (preprint on arXiv)
- **Bib Cites Formal Published Version:** N/A (cites arXiv preprint)
- **Mismatches / Discrepancies Verbatim:**
  * None (all fields match arXiv record verbatim).
- **Date of Fetch:** 2026-10-15

---

## 35. Entry `ascent2026`

- **Bib Key:** `ascent2026`
- **Bib File Locations:**
  * `/home/control/audit/fab376a/docs/paper/arxiv/refs.bib`: lines 327–332
  * `/home/control/audit/fab376a/docs/paper/bar/refs.bib`: lines 327–332
- **Cited in `docs/paper/arxiv`:** **Yes** (1 occurrence)
  * `fab376a/docs/paper/arxiv/sections/related_work.tex:20`: `experience into weights instead: ASCENT~\citep{ascent2026} self-distils`
- **Cited in `docs/paper/bar`:** **No** (0 occurrences in `fab376a/docs/paper/bar/main.tex` and `acfd91d/docs/paper/bar/main.tex`)

**BibTeX Entry as Written:**
```bibtex
327: @article{ascent2026,
328:   title   = {{ASCENT: Online Test-Time Training of Long-Horizon Agents via Self-Distillation of Verified Experience}},
329:   author  = {Lu, Haodong and Gong, Dong},
330:   journal = {arXiv preprint arXiv:2610.05303},
331:   year    = {2026}
332: }
```

**Authoritative Metadata (Fetched 2026-10-15):**
- **Authoritative Title:** ASCENT: Online Test-Time Training of Long-Horizon Agents via Self-Distillation of Verified Experience
- **Authoritative Authors (2 authors):** Haodong Lu, Dong Gong
- **Authoritative Venue:** arXiv preprint arXiv:2610.05303
- **Authoritative Year:** 2026
- **Authoritative URL:** https://arxiv.org/abs/2610.05303
- **Formal Published Version Exists:** No (preprint on arXiv)
- **Bib Cites Formal Published Version:** N/A (cites arXiv preprint)
- **Mismatches / Discrepancies Verbatim:**
  * None (all fields match arXiv record verbatim).
- **Date of Fetch:** 2026-10-15

---

## 36. Entry `edge2026`

- **Bib Key:** `edge2026`
- **Bib File Locations:**
  * `/home/control/audit/fab376a/docs/paper/arxiv/refs.bib`: lines 333–339
  * `/home/control/audit/fab376a/docs/paper/bar/refs.bib`: lines 333–339
- **Cited in `docs/paper/arxiv`:** **Yes** (1 occurrence)
  * `fab376a/docs/paper/arxiv/sections/related_work.tex:21`: `verified trajectories into the weights at test time, EDGE~\citep{edge2026}`
- **Cited in `docs/paper/bar`:** **Yes** (1 occurrence)
  * `fab376a/docs/paper/bar/main.tex:165`: `the policy~\citep{edge2026}, and architectural test-time and self-editing`

**BibTeX Entry as Written:**
```bibtex
333: @article{edge2026,
334:   title   = {{EDGE: Experience-Distillation for Guided Exploration in Agentic Reinforcement Learning}},
335:   author  = {Xie, Can and Zhou, Yuyi and Yang, Wen and Zhang, Ziyi and Song, Siyao and others},
336:   journal = {arXiv preprint arXiv:2608.21946},
337:   year    = {2026},
338:   note    = {Accepted to EMNLP 2026 (Main Conference)}
339: }
```

**Authoritative Metadata (Fetched 2026-10-15):**
- **Authoritative Title:** EDGE: Experience-Distillation for Guided Exploration in Agentic Reinforcement Learning
- **Authoritative Authors (8 authors):** Can Xie, Yuyi Zhou, Wen Yang, Ziyi zhang, Siyao Song, Yingzhuo Deng, Shuo Ren, Jiajun Zhang
- **Authoritative Venue:** arXiv preprint arXiv:2608.21946 (Accepted to EMNLP 2026 Main Conference)
- **Authoritative Year:** 2026
- **Authoritative URL:** https://arxiv.org/abs/2608.21946
- **Formal Published Version Exists:** Yes (accepted to EMNLP 2026; conference proceedings not yet published at fetch date)
- **Bib Cites Formal Published Version:** Cites arXiv preprint with note `Accepted to EMNLP 2026 (Main Conference)`
- **Mismatches / Discrepancies Verbatim:**
  * Author list truncated: bib lists first 5 authors + `others`; arXiv landing page lists 8 authors.
  * Author 4 casing: on arXiv listed as `Ziyi zhang` (lowercase 'z'); bib gives `Zhang, Ziyi`.
- **Date of Fetch:** 2026-10-15

---

## 37. Entry `whenretrieval2026`

- **Bib Key:** `whenretrieval2026`
- **Bib File Locations:**
  * `/home/control/audit/fab376a/docs/paper/arxiv/refs.bib`: lines 340–346
  * `/home/control/audit/fab376a/docs/paper/bar/refs.bib`: lines 340–346
- **Cited in `docs/paper/arxiv`:** **Yes** (1 occurrence)
  * `fab376a/docs/paper/arxiv/sections/related_work.tex:47`: `settings~\citep{whenretrieval2026}, and test-time retrieval helps most where`
- **Cited in `docs/paper/bar`:** **No** (0 occurrences in `fab376a/docs/paper/bar/main.tex` and `acfd91d/docs/paper/bar/main.tex`)

**BibTeX Entry as Written:**
```bibtex
340: @article{whenretrieval2026,
341:   title   = {{When Does Retrieval Help? A Study of In-Context Adaptation in Vision-Language-Action Models}},
342:   author  = {Liu, Zixuan and K{\"o}ster, Joris and Zheng, Zizhan and Khajavi, Siavash},
343:   journal = {arXiv preprint arXiv:2610.05492},
344:   year    = {2026},
345:   note    = {NeurIPS 2026 Workshop PTA}
346: }
```

**Authoritative Metadata (Fetched 2026-10-15):**
- **Authoritative Title:** When Does Retrieval Help? A Study of In-Context Adaptation in Vision-Language-Action Models
- **Authoritative Authors (4 authors):** Zixuan Liu, Joris Köster, Zizhan Zheng, Siavash Khajavi
- **Authoritative Venue:** arXiv preprint arXiv:2610.05492 (NeurIPS 2026 Workshop PTA)
- **Authoritative Year:** 2026
- **Authoritative URL:** https://arxiv.org/abs/2610.05492
- **Formal Published Version Exists:** Accepted to workshop (not yet published in formal proceedings volume at fetch date)
- **Bib Cites Formal Published Version:** Cites arXiv preprint with note `NeurIPS 2026 Workshop PTA`
- **Mismatches / Discrepancies Verbatim:**
  * None against arXiv record (note matches workshop acceptance).
- **Date of Fetch:** 2026-10-15

---

## 38. Entry `reusebefore2026`

- **Bib Key:** `reusebefore2026`
- **Bib File Locations:**
  * `/home/control/audit/fab376a/docs/paper/arxiv/refs.bib`: lines 347–353
  * `/home/control/audit/fab376a/docs/paper/bar/refs.bib`: lines 347–353
- **Cited in `docs/paper/arxiv`:** **Yes** (1 occurrence)
  * `fab376a/docs/paper/arxiv/sections/related_work.tex:48`: `the frozen policy lacks the relevant action prior~\citep{reusebefore2026}.`
- **Cited in `docs/paper/bar`:** **No** (0 occurrences in `fab376a/docs/paper/bar/main.tex` and `acfd91d/docs/paper/bar/main.tex`)

**BibTeX Entry as Written:**
```bibtex
347: @article{reusebefore2026,
348:   title   = {{Reuse Before You Retrieve: Diagnosing Headroom and Complementarity for Test-Time Augmentation of Embodied Multimodal Policies}},
349:   author  = {Jeong, Yuhwan and Yoon, Kuk-Jin},
350:   journal = {arXiv preprint arXiv:2608.17484},
351:   year    = {2026},
352:   note    = {Accepted to an ECCV 2026 workshop}
353: }
```

**Authoritative Metadata (Fetched 2026-10-15):**
- **Authoritative Title:** Reuse Before You Retrieve: Diagnosing Headroom and Complementarity for Test-Time Augmentation of Embodied Multimodal Policies
- **Authoritative Authors (2 authors):** Yuhwan Jeong, Kuk-Jin Yoon
- **Authoritative Venue:** arXiv preprint arXiv:2608.17484 (ECCV 2026 workshop)
- **Authoritative Year:** 2026
- **Authoritative URL:** https://arxiv.org/abs/2608.17484
- **Formal Published Version Exists:** Accepted to workshop (not yet published in formal proceedings volume at fetch date)
- **Bib Cites Formal Published Version:** Cites arXiv preprint with note `Accepted to an ECCV 2026 workshop`
- **Mismatches / Discrepancies Verbatim:**
  * None against arXiv record (note matches workshop acceptance).
- **Date of Fetch:** 2026-10-15

---

## 39. Entry `worldmodelft2026`

- **Bib Key:** `worldmodelft2026`
- **Bib File Locations:**
  * `/home/control/audit/fab376a/docs/paper/arxiv/refs.bib`: lines 354–359
  * `/home/control/audit/fab376a/docs/paper/bar/refs.bib`: lines 354–359
- **Cited in `docs/paper/arxiv`:** **Yes** (1 occurrence)
  * `fab376a/docs/paper/arxiv/sections/related_work.tex:9`: `data-efficient~\citep{worldmodelft2026}, and a holistic comparison of memory`
- **Cited in `docs/paper/bar`:** **No** (0 occurrences in `fab376a/docs/paper/bar/main.tex` and `acfd91d/docs/paper/bar/main.tex`)

**BibTeX Entry as Written:**
```bibtex
354: @article{worldmodelft2026,
355:   title   = {{How To Train Your World Model: Fine-tuning vs RAG for LM-based World Modeling}},
356:   author  = {Ashok, Dhananjay and Agarwal, Shantanu and Datla, Vivek and May, Jonathan and Samuel, Alfy},
357:   journal = {arXiv preprint arXiv:2610.02542},
358:   year    = {2026}
359: }
```

**Authoritative Metadata (Fetched 2026-10-15):**
- **Authoritative Title:** How To Train Your World Model: Fine-tuning vs RAG for LM-based World Modeling
- **Authoritative Authors (5 authors):** Dhananjay Ashok, Shantanu Agarwal, Vivek Datla, Jonathan May, Alfy Samuel
- **Authoritative Venue:** arXiv preprint arXiv:2610.02542
- **Authoritative Year:** 2026
- **Authoritative URL:** https://arxiv.org/abs/2610.02542
- **Formal Published Version Exists:** No (preprint on arXiv)
- **Bib Cites Formal Published Version:** N/A (cites arXiv preprint)
- **Mismatches / Discrepancies Verbatim:**
  * None (all fields match arXiv record verbatim).
- **Date of Fetch:** 2026-10-15

---

## 40. Entry `unimem2026`

- **Bib Key:** `unimem2026`
- **Bib File Locations:**
  * `/home/control/audit/fab376a/docs/paper/arxiv/refs.bib`: lines 360–365
  * `/home/control/audit/fab376a/docs/paper/bar/refs.bib`: lines 360–365
- **Cited in `docs/paper/arxiv`:** **Yes** (1 occurrence)
  * `fab376a/docs/paper/arxiv/sections/related_work.tex:24`: `UniMem~\citep{unimem2026} routes recurring patterns to weights and sparse`
- **Cited in `docs/paper/bar`:** **No** (0 occurrences in `fab376a/docs/paper/bar/main.tex` and `acfd91d/docs/paper/bar/main.tex`)

**BibTeX Entry as Written:**
```bibtex
360: @article{unimem2026,
361:   title   = {{UniMem: Complementary Episodic-to-Parametric Memory for Boundary-Agnostic Task Streams}},
362:   author  = {Xia, Siyu and Zhang, Chenheng and Wu, Yanting and Li, Haoxuan and Chai, Jiajun and others},
363:   journal = {arXiv preprint arXiv:2607.26017},
364:   year    = {2026}
365: }
```

**Authoritative Metadata (Fetched 2026-10-15):**
- **Authoritative Title:** UniMem: Complementary Episodic-to-Parametric Memory for Boundary-Agnostic Task Streams
- **Authoritative Authors (11 authors):** Siyu Xia, Chenheng Zhang, Yanting Wu, Haoxuan Li, Jiajun Chai, Xiaohan Wang, Guojun Yin, Wei Lin, Zhouchen Lin, Haifeng Zhang, Jun Wang
- **Authoritative Venue:** arXiv preprint arXiv:2607.26017
- **Authoritative Year:** 2026
- **Authoritative URL:** https://arxiv.org/abs/2607.26017
- **Formal Published Version Exists:** No (preprint on arXiv)
- **Bib Cites Formal Published Version:** N/A (cites arXiv preprint)
- **Mismatches / Discrepancies Verbatim:**
  * Author list truncated: bib lists first 5 authors + `others`; arXiv landing page lists 11 authors.
- **Date of Fetch:** 2026-10-15

---

## 41. Entry `harnessmem2026`

- **Bib Key:** `harnessmem2026`
- **Bib File Locations:**
  * `/home/control/audit/fab376a/docs/paper/arxiv/refs.bib`: lines 366–371
  * `/home/control/audit/fab376a/docs/paper/bar/refs.bib`: lines 366–371
- **Cited in `docs/paper/arxiv`:** **Yes** (1 occurrence)
  * `fab376a/docs/paper/arxiv/sections/related_work.tex:10`: `substrates finds none dominant~\citep{harnessmem2026}; recent work`
- **Cited in `docs/paper/bar`:** **No** (0 occurrences in `fab376a/docs/paper/bar/main.tex` and `acfd91d/docs/paper/bar/main.tex`)

**BibTeX Entry as Written:**
```bibtex
366: @article{harnessmem2026,
367:   title   = {{Harness the Memory: A Holistic Evaluation of Memory Substrates in Memory Agents}},
368:   author  = {Huang, Wei-Chieh and Zhang, Weizhi and Wu, Yuchen and Chen, Yankai and Jiang, Eric Hanchen and others},
369:   journal = {arXiv preprint arXiv:2608.15008},
370:   year    = {2026}
371: }
```

**Authoritative Metadata (Fetched 2026-10-15):**
- **Authoritative Title:** Harness the Memory: A Holistic Evaluation of Memory Substrates in Memory Agents
- **Authoritative Authors (15 authors):** Wei-Chieh Huang, Weizhi Zhang, Yuchen Wu, Yankai Chen, Eric Hanchen Jiang, Wooseong Yang, Yiwei Yang, Henry Peng Zou, Hanrong Zhang, Ying Nian Wu, Haolun Wu, Kai-Wei Chang, Philip S. Yu, Xue Liu, Aylin Caliskan
- **Authoritative Venue:** arXiv preprint arXiv:2608.15008
- **Authoritative Year:** 2026
- **Authoritative URL:** https://arxiv.org/abs/2608.15008
- **Formal Published Version Exists:** No (preprint on arXiv)
- **Bib Cites Formal Published Version:** N/A (cites arXiv preprint)
- **Mismatches / Discrepancies Verbatim:**
  * Author list truncated: bib lists first 5 authors + `others`; arXiv landing page lists 15 authors.
- **Date of Fetch:** 2026-10-15

---
