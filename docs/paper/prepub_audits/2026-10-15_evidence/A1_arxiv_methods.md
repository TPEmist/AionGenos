| id | file:line | exact literal (verbatim, plus surrounding 8 words) | what it measures | cited source in text or 'none' |
|---|---|---|---|---|
| M1 | methods_d11.tex:17 | active end-effector comes within 0.05 m of the target; each episode | Distance threshold for reach task episode success | none |
| M2 | methods_d11.tex:18 | subject to an inherited 24\,s environment auto-reset, \S3.5), where | Environment auto-reset timeout duration | none |
| M3 | methods_d11.tex:19 | where a \emph{round} is one VLM reasoning step followed by an inverse-kinematics | Definition of round budget unit (1 VLM reasoning step) | none |
| M4 | methods_d11.tex:26 | The teacher is Gemma-4-31B-it~\citep{gemma2024} (multimodal, 4-bit) served via | Base teacher language model parameter count (31 billion parameters) | \citep{gemma2024} |
| M5 | methods_d11.tex:26 | is Gemma-4-31B-it~\citep{gemma2024} (multimodal, 4-bit) served via llama.cpp, augmented with | Teacher model weight quantization precision | \citep{gemma2024} |
| M6 | methods_d11.tex:28 | writes a self-recap; at round 1 of a new episode it retrieves the | Episode round index at which past lessons retrieval occurs | none |
| M7 | methods_d11.tex:40 | \subsection*{3.3 Students, arms, and the 2$\times$2 factorial} | Factorial experimental design structure (gist x native thought) | none |
| M8 | methods_d11.tex:42 | LoRA~\citep{lora2021} adapters (rank-16, $\alpha$=32, dropout 0.05) on the | LoRA adapter intrinsic rank parameter | \citep{lora2021} |
| M9 | methods_d11.tex:42 | adapters (rank-16, $\alpha$=32, dropout 0.05) on the same Gemma-4-31B-it | LoRA adapter scaling hyperparameter alpha | \citep{lora2021} |
| M10 | methods_d11.tex:42 | (rank-16, $\alpha$=32, dropout 0.05) on the same Gemma-4-31B-it base, | LoRA adapter dropout rate | \citep{lora2021} |
| M11 | methods_d11.tex:45 | Each arm is trained in two stages on the \emph{same} pinned trajectory pool: | Number of sequential training stages per arm | none |
| M12 | methods_d11.tex:46 | trajectory pool: SFT (stage 4-A, 992 desirable progress-rounds, 1 epoch, lr 2e-4) followed | SFT training dataset sample size in desirable progress-rounds | none |
| M13 | methods_d11.tex:47 | 992 desirable progress-rounds, 1 epoch, lr 2e-4) followed by composable-KTO~\citep{kto2024} | Training duration in epochs for SFT stage | none |
| M14 | methods_d11.tex:47 | desirable progress-rounds, 1 epoch, lr 2e-4) followed by composable-KTO~\citep{kto2024} refinement | Learning rate hyperparameter for SFT stage | none |
| M15 | methods_d11.tex:48 | refinement (stage 4-B, 992 desirable + 1799 undesirable rounds, 1 epoch, lr 5e-5, $\beta$=0.1, | Sample counts of desirable and undesirable rounds for KTO training | \citep{kto2024} |
| M16 | methods_d11.tex:48 | 992 desirable + 1799 undesirable rounds, 1 epoch, lr 5e-5, $\beta$=0.1, auto-balanced class | Training duration in epochs for KTO refinement stage | \citep{kto2024} |
| M17 | methods_d11.tex:48 | undesirable rounds, 1 epoch, lr 5e-5, $\beta$=0.1, auto-balanced class weights) | Learning rate hyperparameter for KTO refinement stage | \citep{kto2024} |
| M18 | methods_d11.tex:49 | 1 epoch, lr 5e-5, $\beta$=0.1, auto-balanced class weights) with the frozen | KTO loss hyperparameter beta | \citep{kto2024} |
| M19 | methods_d11.tex:54 | The four training arms form a 2$\times$2 factorial over two | Number of student training arms | none |
| M20 | methods_d11.tex:54 | four training arms form a 2$\times$2 factorial over two binary factors --- retrieved-lesson | Factorial experimental design dimension | none |
| M21 | methods_d11.tex:54 | form a 2$\times$2 factorial over two binary factors --- retrieved-lesson gist in the target, | Number of binary factors varied in the study | none |
| M22 | methods_d11.tex:72 | All four arms are pinned to the identical 2791-round | Number of training arms pinned to the common pool | none |
| M23 | methods_d11.tex:72 | arms are pinned to the identical 2791-round pool (992 desirable + 1799 undesirable), | Total round count of pinned training trajectory pool | Appendix A1, Amendments 12--13 |
| M24 | methods_d11.tex:72 | the identical 2791-round pool (992 desirable + 1799 undesirable), verified by SHA-256 before training | Desirable and undesirable round composition of pinned pool | Appendix A1, Amendments 12--13 |
| M25 | methods_d11.tex:73 | (992 desirable + 1799 undesirable), verified by SHA-256 before training (Appendix A1, Amendments 12--13); | Cryptographic hash algorithm bit width used for dataset verification | Appendix A1, Amendments 12--13 |
| M26 | methods_d11.tex:79 | Five inference protocols are evaluated, 100 episodes each, all at | Number of inference protocols evaluated | none |
| M27 | methods_d11.tex:79 | Five inference protocols are evaluated, 100 episodes each, all at the same task with | Evaluation sample size (number of episodes per protocol) | none |
| M28 | methods_d11.tex:97 | C\_retrieval is \emph{not} a fifth trained arm: it reuses A\_ctrl\_rat's adapter weights | Ordinal count of arms clarifying C_retrieval is not an additional trained arm | none |
| M29 | methods_d11.tex:99 | an inference-time PAST\_LESSONS preamble. Two contrasts therefore follow, and we keep them distinct | Number of primary comparative contrasts examined | none |
| M30 | methods_d11.tex:114 | All five protocols share a fixed environment seed base (4500; | Number of protocols sharing seed base | Amendment 11 |
| M31 | methods_d11.tex:114 | share a fixed environment seed base (4500; per- episode seed = 4500 + | Environment base random seed for paired evaluation | Amendment 11 |
| M32 | methods_d11.tex:115 | environment seed base (4500; per- episode seed = 4500 + episode index), so episode \emph{k} starts | Formula for deterministic per-episode seed assignment | Amendment 11 |
| M33 | methods_d11.tex:125 | B\_main $-$ A\_action\_only. Rejection: $\Delta$ SR $\ge$ +10 pp AND significant, two-sided, $\alpha$=0.020. | Rejection threshold for primary hypothesis T1 in percentage points | pre-reg \S2--\S4, refined by Amendments 9--10 |
| M34 | methods_d11.tex:126 | $\Delta$ SR $\ge$ +10 pp AND significant, two-sided, $\alpha$=0.020. A graded reading within this budget | Significance level alpha for primary hypothesis T1 | pre-reg \S2--\S4, refined by Amendments 9--10 |
| M35 | methods_d11.tex:127 | within this budget line: T1-strong ($\ge$+10 pp) and T1-weak ($>$0, significant at | Success rate difference threshold for T1-strong outcome | pre-reg \S2--\S4, refined by Amendments 9--10 |
| M36 | methods_d11.tex:127 | T1-strong ($\ge$+10 pp) and T1-weak ($>$0, significant at $\alpha$=0.010). Explicit falsification | Success rate difference threshold for T1-weak outcome | pre-reg \S2--\S4, refined by Amendments 9--10 |
| M37 | methods_d11.tex:128 | T1-weak ($>$0, significant at $\alpha$=0.010). Explicit falsification clause on the memory-in-weights | Significance level alpha for T1-weak outcome | pre-reg \S2--\S4, refined by Amendments 9--10 |
| M38 | methods_d11.tex:130 | \textbf{T1a}: B\_main $-$ A\_ctrl\_rat, two-sided, $\alpha$=0.020. | Significance level alpha for hypothesis T1a test | pre-reg \S2--\S4, refined by Amendments 9--10 |
| M39 | methods_d11.tex:131 | \textbf{T4}: C\_retrieval $-$ B\_main, two-sided, $\alpha$=0.010. | Significance level alpha for hypothesis T4 test | pre-reg \S2--\S4, refined by Amendments 9--10 |
| M40 | methods_d11.tex:132 | \item \textbf{T3}: B\_main SR $\ge$ 0.7 $\times$ pooled memory-teacher SR (=36.2\%), one-sided. | Multiplier threshold for T3 retention hypothesis test | pre-reg \S2--\S4, refined by Amendments 9--10 |
| M41 | methods_d11.tex:132 | 0.7 $\times$ pooled memory-teacher SR (=36.2\%), one-sided. | Pooled memory-augmented teacher baseline success rate | pre-reg \S2--\S4, refined by Amendments 9--10 |
| M42 | methods_d11.tex:134 | \item Family-wise $\alpha$=0.060 (Amendment 10, non-uniform allocation). | Total allocated family-wise significance level alpha | Amendment 10 |
| M43 | methods_d11.tex:137 | Amendment 14 \S14.5, with pre-registered per-arm predictions): round-1 target X minus initial EE X, per | Episode round index for R1 lateral displacement probe | Amendment 9 \S9.3; Amendment 14 \S14.5 |
| M44 | methods_d11.tex:138 | scalar-guard grid units (1 unit $=$ 0.45\,cm along x; the pre-registration labelled them cm; | Physical conversion factor between grid units and centimeters along x-axis | Amendment 16, 730b9fc |
| M45 | methods_d11.tex:140 | erratum, Amendment 16, \texttt{730b9fc}), against two reference fingerprints (memoryless-teacher $-$23.5, memory-teacher last-quartile | Number of reference fingerprints for R1 displacement | Amendment 16, 730b9fc |
| M46 | methods_d11.tex:141 | two reference fingerprints (memoryless-teacher $-$23.5, memory-teacher last-quartile $-$15.8), with | Reference lateral displacement fingerprint for memoryless teacher in grid units | Amendment 9 \S9.3 |
| M47 | methods_d11.tex:141 | (memoryless-teacher $-$23.5, memory-teacher last-quartile $-$15.8), with a registered branch choice | Reference lateral displacement fingerprint for memory-augmented teacher last quartile in grid units | Amendment 9 \S9.3 |
| M48 | methods_d11.tex:144 | the task inherits a 24\,s environment time-out (720 steps) that auto-resets | Inherited environment auto-reset timeout duration in seconds | Amendment 15 pin 8 |
| M49 | methods_d11.tex:145 | 24\,s environment time-out (720 steps) that auto-resets inside the environment step, | Inherited environment auto-reset timeout step count | Amendment 15 pin 8 |
| M50 | methods_d11.tex:147 | continue on a re-sampled configuration (boundary at trajectory index 718, located per episode from the step | Trajectory step index boundary for auto-reset sensitivity analysis | Amendment 15 pin 8 |
| M51 | methods_d11.tex:161 | for each episode index, a 5-way \texttt{allclose} ($\varepsilon$=1e-4 m) on the | Number of protocols checked simultaneously in pairing integrity gate | Amendment 14 |
| M52 | methods_d11.tex:162 | a 5-way \texttt{allclose} ($\varepsilon$=1e-4 m) on the initial configuration; on failure, | Distance tolerance epsilon for pairing integrity gate in meters | Amendment 14 |
| M53 | methods_d11.tex:171 | persist pre-action cube pose and the first trajectory sample is already one servo-step in; a frozen-arm | Simulation servo-step offset of first recorded replay sample | none |
| M54 | methods_d11.tex:171 | diagnostic (seed identical 100/100, frozen right-arm identical 100/100, active | Seed match frequency across evaluated protocols (100 out of 100 episodes) | none |
| M55 | methods_d11.tex:172 | (seed identical 100/100, frozen right-arm identical 100/100, active left-arm 1/100) confirms the | Frozen right-arm pose match frequency across protocols (100 out of 100 episodes) | none |
| M56 | methods_d11.tex:172 | frozen right-arm identical 100/100, active left-arm 1/100) confirms the pairing is physically real. | Active left-arm pose match frequency across protocols (1 out of 100 episodes) | none |
| M57 | methods_d11.tex:179 | training targets passed a deterministic three-rule rationale filter (direction-consistency, ground-truth geometry, vacuity). | Number of heuristic rules in deterministic rationale filter | none |
| M58 | methods_d11.tex:181 | ground-truth geometry, vacuity). Over three blinded-audit rounds the first two rules were | Number of blinded audit evaluation rounds conducted on filter | none |
| M59 | methods_d11.tex:181 | Over three blinded-audit rounds the first two rules were found to measure \emph{coherence}, | Count of filter rules evaluated for correctness | none |
| M60 | methods_d11.tex:184 | Amendment 13) zero drop authority under the \texttt{flags\_only\_a6} policy actually used, so | Row dropping authority count under flags_only_a6 policy | Amendment 13 |
| M61 | methods_d11.tex:185 | the filter drops no rows and the four arms' 992/2791 counts are filter-invariant. | Count of student training arms | none |
| M62 | methods_d11.tex:185 | no rows and the four arms' 992/2791 counts are filter-invariant. We report this | Ratio of desirable rounds (992) to total rounds (2791) in training pool | none |
| M63 | methods_d11.tex:193 | before the step it governed. Amendments 1--13 were filed before any adapter trained; | Range of pre-training amendment numbers | none |
| M64 | methods_d11.tex:194 | Amendments 1--13 were filed before any adapter trained; Amendment 14 was filed after collection but before | Number of post-collection pre-analysis decision lock amendment | none |
| M65 | methods_d11.tex:205 | blinded audit; escalation rule (agreement $<$85\% $\rightarrow$ LLM judge) & --- | Inter-rater agreement percentage threshold triggering escalation to LLM judge | none |
| M66 | methods_d11.tex:207 | 4 & 07-07 & Rule-1 sentence classifier (past/intent) fix & | Identifier/index of sentence classifier filter rule | none |
| M67 | methods_d11.tex:208 | 5 & 07-07 & Rule-2 demoted to flag; composite-agreement rejected & | Identifier/index of geometry filter rule demoted to flag | 6a29103 |
| M68 | methods_d11.tex:209 | Coherence filter $\rightarrow$ advisory flags (v-final 992+1810) & 9b0a9da \\ | Intermediate training dataset round counts (992 desirable + 1810 undesirable) | 9b0a9da |
| M69 | methods_d11.tex:211 | target hygiene + 2$\times$2 + C\_retrieval protocol & 1a44d61 | Factorial experimental design dimension | 1a44d61 / a7bada2 |
| M70 | methods_d11.tex:214 | design $\rightarrow$ McNemar; env\_seed\_base=4500; SHA gate & bfa7cc6 \\ | Pinned base environment random seed value | bfa7cc6 |
| M71 | methods_d11.tex:216 | 13 & 07-08 & Step-2 row-count sentinel; structural \texttt{flags\_only\_a6} | Pipeline stage index for row-count sentinel check | 9f5bec1 / cd1eb94 |
| M72 | methods_d11.tex:222 | \emph{(Amendments 5--13 were filed 07-07/07-08 in the | Range of amendment numbers filed in pre-flight window | none |
| M73 | methods_d11.tex:227 | pinned at each amendment's date; the final training counts are 992 + 1799 (Amendment 8 | Final pinned training round counts (992 desirable + 1799 undesirable) | Amendment 8 |
| M74 | methods_d11.tex:227 | counts are 992 + 1799 (Amendment 8 re-pinned from A6's 992 + 1810 after a | Amendment 6 pinned training round counts (992 desirable + 1810 undesirable) | A6 (Amendment 6) |
| M75 | methods_d11.tex:228 | a trajectory-set ID diff removed 11 no-retrieval-hit rounds from a single episode). | Count of excluded training rounds lacking retrieval hits | Amendment 8 |
| M76 | methods_d11.tex:228 | removed 11 no-retrieval-hit rounds from a single episode). The methods body uses the | Episode count affected by round removal (1 episode) | none |
| M77 | methods_d11.tex:229 | from a single episode). The methods body uses the final 1799. | Final undesirable round count used in training | none |
| M78 | methods_d11.tex:233 | Three blinded audit rounds on the deterministic filter's drop surface; Rules | Number of blinded audit evaluation rounds on filter performance | none |
| M79 | methods_d11.tex:234 | filter's drop surface; Rules 1--2 precision on the correctness axis was | Evaluated filter rule indices (Rules 1 and 2) | Amendments 4--6 |
| M80 | methods_d11.tex:236 | in the final pipeline is a structural zero-drop guarantee (Amendment 13): all three rules | Guarantee of zero dropped rows under flags_only_a6 policy | Amendment 13 |
| M81 | methods_d11.tex:237 | guarantee (Amendment 13): all three rules compute and emit advisory flags, none | Count of active advisory filter rules | Amendment 13 |
| M82 | methods_d11.tex:238 | none drops a row, so the 992/2791 pool is filter-invariant and the cross-arm | Training pool composition (992 desirable / 2791 total rounds) | Amendment 13 |
| M83 | methods_l2.tex:20 | dual-arm position-goal reaching in a 6-DoF control space (Amendment 1 \S2) | Degrees of freedom of control space for L2 task | Amendment 1 \S2 |
| M84 | methods_l2.tex:22 | dual-arm position-goal reaching task in a 6-DoF control space (renamed from the working | Degrees of freedom of robot control action space | Amendment 1 \S2 |
| M85 | methods_l2.tex:28 | although the control space is 6-DoF and the state carries RPY, the | Degrees of freedom of control space | Amendment 3 \S4 |
| M86 | methods_l2.tex:29 | success gate are \textbf{position-only} ($\Vert$EE$-$target$\Vert$ $<$ 0.05 m; no RPY term is scored). | Position tolerance distance threshold for reach success | Amendment 3 \S4 |
| M87 | methods_l2.tex:32 | reaching in a 6-DoF control space'', not ``6-DoF pose-reach''. The paper | Degrees of freedom of control space in task description | none |
| M88 | methods_l2.tex:41 | simultaneously at episode end) was \textbf{1/100} on the L2 collect; per-arm | Joint success rate holding tolerance simultaneously at episode end in L2 collect | Amendment 1 \S1 |
| M89 | methods_l2.tex:41 | on the L2 collect; per-arm success was \textbf{28/100 left, 28/100 right}. Each arm reaching | Per-arm success counts out of 100 episodes for left and right arms in L2 collect | Amendment 1 \S1 |
| M90 | methods_l2.tex:42 | Each arm reaching its goal at some point (best-in-episode, 28/100; both arms in | Best-in-episode individual arm reach success rate | none |
| M91 | methods_l2.tex:43 | point (best-in-episode, 28/100; both arms in 10/100) is not the same event as | Best-in-episode proportion of episodes where both arms reached tolerance at some point | none |
| M92 | methods_l2.tex:44 | both holding tolerance simultaneously at episode end (1/100), so the primary L2 metric is | Joint success rate holding tolerance at episode termination | none |
| M93 | methods_l2.tex:54 | its pose goal (best-in-episode $\Vert$EE$-$target$\Vert$ $<$ 0.05 m, the registered threshold) $\rightarrow$ | Distance tolerance threshold for desirable episode determination | none |
| M94 | methods_l2.tex:55 | threshold) $\rightarrow$ $\approx$28 desirable-arm instances per arm. \item \textbf{SFT target} | Approximate count of desirable episode instances available per arm | none |
| M95 | methods_l2.tex:70 | The 100 L2 recaps were tagged \texttt{is\_success} by JOINT | Total count of episodic memory recaps in L2 buffer | none |
| M96 | methods_l2.tex:71 | tagged \texttt{is\_success} by JOINT outcome at collect time (1 True / 99 False). Full-population | Breakdown of boolean success tags assigned by joint outcome in original L2 recaps | none |
| M97 | methods_l2.tex:71 | (1 True / 99 False). Full-population re-score: 46/100 episodes have $\ge$1 arm reaching | Proportion of L2 episodes where at least one arm reached goal | workspace/l2_audit/per_arm_rescore.json |
| M98 | methods_l2.tex:72 | Full-population re-score: 46/100 episodes have $\ge$1 arm reaching goal, of which \textbf{45 | Arm count threshold for partial episode success | workspace/l2_audit/per_arm_rescore.json |
| M99 | methods_l2.tex:72 | have $\ge$1 arm reaching goal, of which \textbf{45 carry \texttt{is\_success=False} despite holding | Number of episodes carrying false negative success label under per-arm criterion | workspace/l2_audit/per_arm_rescore.json |
| M100 | methods_l2.tex:74 | so under per-arm scoring the buffer's labels are wrong for $\approx$45\% of episodes, and | Percentage of recap buffer labels that are incorrect under per-arm scoring | none |
| M101 | methods_l2.tex:96 | (Amendment 1a): re-tag $\rightarrow$ 3--5-line retriever change $\rightarrow$ re-pin buffer SHA | Size of code change in lines required for retriever logic update | Amendment 1a |
| M102 | methods_l2.tex:98 | tree-hash \texttt{83337879\ldots}, post-retag \texttt{a79581cd\ldots}, 100/100 recaps dual-labelled. The teacher's joint-labelled | Count of L2 recaps updated with dual per-arm labels | none |
| M103 | methods_l2.tex:105 | L2's desirable pool is 511 per-arm rounds from 56 per-arm | Number of desirable training rounds in L2 per-arm dataset | Amendment 2 |
| M104 | methods_l2.tex:105 | pool is 511 per-arm rounds from 56 per-arm episode-instances (vs L0a's 992 | Number of desirable episode-arm instances in L2 training pool | Amendment 2 |
| M105 | methods_l2.tex:106 | 56 per-arm episode-instances (vs L0a's 992 desirable rounds). The two D11 headlines | Reference desirable round count from L0a dataset | none |
| M106 | methods_l2.tex:108 | at this n; L2 therefore tests \textbf{one} question, not a symmetric 2$\times$2 | Number of primary hypotheses evaluated in L2 | Amendment 2 |
| M107 | methods_l2.tex:108 | tests \textbf{one} question, not a symmetric 2$\times$2 (Amendment 2): \begin{itemize} | Full factorial experimental design dimensions | Amendment 2 |
| M108 | methods_l2.tex:112 | A\_ctrl\_rat)} --- D11's strongest result (+34 pp, z=5.15). At L2 baseline | D11 headline retrieval effect size in percentage points | none |
| M109 | methods_l2.tex:112 | --- D11's strongest result (+34 pp, z=5.15). At L2 baseline $\approx$15\%, | Two-proportion z-statistic for D11 headline retrieval effect | none |
| M110 | methods_l2.tex:112 | result (+34 pp, z=5.15). At L2 baseline $\approx$15\%, power at n=100, $\alpha$=0.010 | Assumed baseline success rate for L2 power calculation | none |
| M111 | methods_l2.tex:113 | At L2 baseline $\approx$15\%, power at n=100, $\alpha$=0.010 is \textbf{76\% (+20 | Sample size assumed for statistical power analysis | none |
| M112 | methods_l2.tex:113 | baseline $\approx$15\%, power at n=100, $\alpha$=0.010 is \textbf{76\% (+20 pp) | Significance level alpha assumed for statistical power analysis | none |
| M113 | methods_l2.tex:113 | at n=100, $\alpha$=0.010 is \textbf{76\% (+20 pp) / 99\% (+30 pp) | Statistical power (76%) at effect size of +20 pp | none |
| M114 | methods_l2.tex:113 | \textbf{76\% (+20 pp) / 99\% (+30 pp) / 100\% (+34 pp)}. | Statistical power (99%) at effect size of +30 pp | none |
| M115 | methods_l2.tex:113 | (+20 pp) / 99\% (+30 pp) / 100\% (+34 pp)}. Detectable --- this is the | Statistical power (100%) at effect size of +34 pp | none |
| M116 | methods_l2.tex:115 | \textbf{T1-class (bake-in)} --- L0a effect +1 pp; L2 critical difference at $\alpha$=0.020, | Observed L0a bake-in effect size (B_main - A_action_only) | none |
| M117 | methods_l2.tex:115 | effect +1 pp; L2 critical difference at $\alpha$=0.020, n=100 is \textbf{12--13 pp} | Significance level alpha for L2 critical difference calculation | none |
| M118 | methods_l2.tex:115 | pp; L2 critical difference at $\alpha$=0.020, n=100 is \textbf{12--13 pp} ($\approx$50\%-power | Sample size per arm for L2 critical difference calculation | none |
| M119 | methods_l2.tex:116 | $\alpha$=0.020, n=100 is \textbf{12--13 pp} ($\approx$50\%-power MDE). A $\approx$1 pp | Critical difference range in percentage points detectable at alpha=0.020 | none |
| M120 | methods_l2.tex:116 | n=100 is \textbf{12--13 pp} ($\approx$50\%-power MDE). A $\approx$1 pp effect | Power level corresponding to minimum detectable effect of 12-13 pp | none |
| M121 | methods_l2.tex:116 | ($\approx$50\%-power MDE). A $\approx$1 pp effect on a 12 pp-critical-difference instrument | Hypothesized true bake-in effect size based on L0a findings | none |
| M122 | methods_l2.tex:116 | A $\approx$1 pp effect on a 12 pp-critical-difference instrument with about half the | Minimum critical difference threshold for significance | none |
| M123 | methods_l2.tex:122 | (the window's scope): train ONE adapter, \textbf{A\_ctrl\_rat}, on all 56 | Number of student adapters trained in Stage 1 | none |
| M124 | methods_l2.tex:123 | ONE adapter, \textbf{A\_ctrl\_rat}, on all 56 desirable episode-instances. Training adequacy (distinct from | Number of desirable episode-arm instances used for training | none |
| M125 | methods_l2.tex:125 | 56 desirable episode-instances expand to \textbf{511 desirable / 1119 undesirable per-arm ROUNDS} | Breakdown of per-arm desirable and undesirable rounds in L2 training dataset | none |
| M126 | methods_l2.tex:126 | on rounds; SFT = 511 behavior-cloning rounds, KTO = 511 + | SFT training round count | none |
| M127 | methods_l2.tex:126 | 511 behavior-cloning rounds, KTO = 511 + 1119). Two eval protocols: A\_ctrl\_rat | KTO training rounds pool sum (511 desirable + 1119 undesirable) | none |
| M128 | methods_l2.tex:126 | KTO = 511 + 1119). Two eval protocols: A\_ctrl\_rat bare + C\_retrieval | Number of evaluation protocols run in Stage 1 | none |
| M129 | methods_l2.tex:142 | retrieval effect} (not of the full 2$\times$2). The observed contrast (\S5.9.1) did | Factorial experimental design structure | Amendment 2 |
| M130 | methods_l2.tex:157 | the joint definition that produced SR = 1/100 and motivated the per-arm re-score. | Success rate under joint both-arms evaluation criterion | none |
| M131 | methods_l2.tex:169 | on the scored arm only ($\Vert$EE\_scored $-$ target\_scored$\Vert$ $<$ 0.05 m), reusing the L0a single-arm | Position tolerance distance threshold for scored arm reach success | none |
| M132 | methods_l2.tex:184 | main eval = LEFT-scored only, 2 protocols $\times$ n=100, seed\_base 4600 shared} | Number of evaluated protocols in confirmatory contrast | Amendment 3 |
| M133 | methods_l2.tex:184 | only, 2 protocols $\times$ n=100, seed\_base 4600 shared} (paired | Evaluation sample size (number of episodes per protocol) | Amendment 3 |
| M134 | methods_l2.tex:184 | 2 protocols $\times$ n=100, seed\_base 4600 shared} (paired McNemar design preserved). | Base random seed for L2 evaluation environments | Amendment 3 |
| M135 | methods_l2.tex:209 | richer \texttt{allclose}, still valid). L2 eval seed base = \textbf{4600} (shared across both | Base environment seed value for L2 evaluation | Amendment 3 \S3 |
| M136 | methods_l2.tex:212 | Amendment 3 \S3), distinct from D11's eval seed base 4500 (the L2 teacher collect | D11 evaluation base environment seed value | none |
| M137 | methods_l2.tex:221 | each arm's own target, reported as a two-component vector ($\Delta$X\_L, $\Delta$X\_R), plus a pooled | Dimension of per-arm displacement vector for L2 R1 probe | l2_analysis_adaptation.md |
| M138 | methods_l2.tex:222 | magnitude $\Vert\Delta$R1$\Vert$} (mean over both arms of $\vert$round-1 target $-$ init EE$\vert$ along the | Round index evaluated for lateral displacement | l2_analysis_adaptation.md |
| M139 | methods_l2.tex:227 | the L2 teacher buffer), \textbf{not} the transplanted L0a $-$23.5/$-$15.8 grid-unit fingerprints. Locked now so | Transplanted L0a teacher reference R1 displacement fingerprints in grid units | none |
| M140 | methods_l2.tex:234 | verify layer twice more (interception rate 3/3 across the program) --- (i) the | Interception success count of pipeline verification layer across program | none |
| M141 | methods_l2.tex:236 | in the \texttt{failure/} replay dir (joint-success 1/100), so pool selection is by per-arm | Proportion of joint success episodes in replay directory | none |
| M142 | methods_l2.tex:238 | a would-be training-semantics error (1119 failed-arm rounds nearly behavior-cloned as desirable), not | Count of failed-arm rounds intercepted from erroneous inclusion in SFT pool | Amendment 2 addendum 2026-07-16 |
| M143 | methods_l2.tex:247 | Methods sentence for each is in l2\_amendment\_2.md. A fourth interception (Amendment 3 \S7) closes a | Ordinal count of pipeline verification interceptions | Amendment 3 \S7 |
| M144 | methods_l2.tex:249 | a single-arm-trained model --- the fourth train/eval output-format mismatch caught in the | Cumulative count of format mismatches encountered | none |
| M145 | methods_l2.tex:250 | but the fourth caught \emph{reactively} (crashing at episode 1). The permanent fix is a | Episode index where evaluation script crashed | none |
| M146 | methods_l2.tex:257 | before the simulator boots. This makes the train/eval-contract interception rate 4/4 and, from here, prospective | Cumulative interception success rate count for train/eval contract assertions | none |
| M147 | methods_l2.tex:269 | Per-arm eval (Amendment 3: left-scored, n=100 paired, seed\_base 4600): \begin{table}[h] | Sample size per protocol in confirmatory per-arm evaluation | Amendment 3 |
| M148 | methods_l2.tex:269 | eval (Amendment 3: left-scored, n=100 paired, seed\_base 4600): \begin{table}[h] \centering \begin{tabular}{l | Base random seed for confirmatory evaluation | Amendment 3 |
| M149 | methods_l2.tex:277 | protocol & successes / n & SR \\ \midrule A\_ctrl\_rat (bare) & 14 / 100 & 14\% | Number of successful episodes out of 100 for bare A_ctrl_rat adapter | scripts/analysis/l2_confirmatory.py (run 8384a740) |
| M150 | methods_l2.tex:277 | \midrule A\_ctrl\_rat (bare) & 14 / 100 & 14\% \\ C\_retrieval (same weights + | Success rate of bare A_ctrl_rat adapter | scripts/analysis/l2_confirmatory.py (run 8384a740) |
| M151 | methods_l2.tex:278 | weights + frozen re-tagged buffer) & 20 / 100 & 20\% \\ \bottomrule \end{tabular} | Number of successful episodes out of 100 for C_retrieval | scripts/analysis/l2_confirmatory.py (run 2154e57e) |
| M152 | methods_l2.tex:278 | frozen re-tagged buffer) & 20 / 100 & 20\% \\ \bottomrule \end{tabular} \end{table} | Success rate of C_retrieval protocol | scripts/analysis/l2_confirmatory.py (run 2154e57e) |
| M153 | methods_l2.tex:283 | identical-weights contrast is \textbf{C\_retrieval $-$ A\_ctrl\_rat = +6.0 pp} (Newcombe 95\% CI \textbf{[$-$4.5, | Difference in success rate between C_retrieval and A_ctrl_rat | scripts/analysis/l2_confirmatory.py |
| M154 | methods_l2.tex:284 | +6.0 pp} (Newcombe 95\% CI \textbf{[$-$4.5, +16.4] pp}). Primary test: | Confidence level of confidence interval | scripts/analysis/l2_confirmatory.py |
| M155 | methods_l2.tex:284 | $-$ A\_ctrl\_rat = +6.0 pp} (Newcombe 95\% CI \textbf{[$-$4.5, +16.4] pp}). Primary test: two-proportion | 95% Newcombe confidence interval for the difference in proportions | scripts/analysis/l2_confirmatory.py |
| M156 | methods_l2.tex:285 | \textbf{[$-$4.5, +16.4] pp}). Primary test: two-proportion z = 1.129, \textbf{p = 0.259, | Two-proportion z-test statistic for confirmatory contrast | scripts/analysis/l2_confirmatory.py |
| M157 | methods_l2.tex:285 | two-proportion z = 1.129, \textbf{p = 0.259, n.s.} at the pre-registered $\alpha$=0.010 | p-value of two-proportion z-test for confirmatory contrast | scripts/analysis/l2_confirmatory.py |
| M158 | methods_l2.tex:285 | \textbf{p = 0.259, n.s.} at the pre-registered $\alpha$=0.010 (T4-class). The paired McNemar was | Pre-registered significance level alpha for T4-class hypothesis test | scripts/analysis/l2_confirmatory.py |
| M159 | methods_l2.tex:288 | (\S5.9.2), and McNemar's discordant cells (9 vs 3; exact McNemar p=0.146) give the | Counts of discordant pairs (9 C_retrieval wins vs 3 A_ctrl_rat wins) | Amendment 14 \S14.2 |
| M160 | methods_l2.tex:288 | discordant cells (9 vs 3; exact McNemar p=0.146) give the same n.s. conclusion. | Exact McNemar test p-value for paired contrast | none |
| M161 | methods_l2.tex:290 | pin 8 rule, \S3.5; L2 inherits the same 24\,s time-out): 10 \texttt{A\_ctrl\_rat} and | Environment timeout duration inherited by L2 | Amendment 15 pin 8 |
| M162 | methods_l2.tex:290 | same 24\,s time-out): 10 \texttt{A\_ctrl\_rat} and 9 \texttt{C\_retrieval} episodes | Count of A_ctrl_rat episodes crossing auto-reset boundary | docs/paper/data/l2_autoreset_sensitivity.json |
| M163 | methods_l2.tex:290 | 10 \texttt{A\_ctrl\_rat} and 9 \texttt{C\_retrieval} episodes cross the boundary | Count of C_retrieval episodes crossing auto-reset boundary | docs/paper/data/l2_autoreset_sensitivity.json |
| M164 | methods_l2.tex:292 | sensitivity counts equal the as-run counts: 20 vs 14, +6.0 pp (z=1.129, p=0.259), | Auto-reset sensitivity success counts (20 for C_retrieval vs 14 for A_ctrl_rat) | docs/paper/data/l2_autoreset_sensitivity.json |
| M165 | methods_l2.tex:292 | as-run counts: 20 vs 14, +6.0 pp (z=1.129, p=0.259), same verdict (\texttt{docs/paper/data/l2\_autoreset\_sensitivity.json}). | Auto-reset sensitivity difference in success rate | docs/paper/data/l2_autoreset_sensitivity.json |
| M166 | methods_l2.tex:292 | 20 vs 14, +6.0 pp (z=1.129, p=0.259), same verdict (\texttt{docs/paper/data/l2\_autoreset\_sensitivity.json}). | Two-proportion z-statistic under auto-reset sensitivity analysis | docs/paper/data/l2_autoreset_sensitivity.json |
| M167 | methods_l2.tex:293 | 14, +6.0 pp (z=1.129, p=0.259), same verdict (\texttt{docs/paper/data/l2\_autoreset\_sensitivity.json}). | p-value of two-proportion z-test under auto-reset sensitivity analysis | docs/paper/data/l2_autoreset_sensitivity.json |
| M168 | methods_l2.tex:297 | is below the pre-registered MDE (+20 pp for 76\% power, Amendment 2); | Pre-registered minimum detectable effect size | Amendment 2 |
| M169 | methods_l2.tex:297 | the pre-registered MDE (+20 pp for 76\% power, Amendment 2); the direction agrees | Statistical power target for MDE | Amendment 2 |
| M170 | methods_l2.tex:301 | branch} (\S5.9.3), not more arms --- and the +6 pp result was predicted n.s. in advance | Observed difference in success rate | none |
| M171 | methods_l2.tex:302 | in advance and is. We do \textbf{not} call +6 pp a positive replication of the effect \emph{size}; | Observed effect size | none |
| M172 | methods_l2.tex:307 | identical across the two protocols on 100/100 episodes, and the frozen right arm | Proportion of episodes sharing identical environment seed | none |
| M173 | methods_l2.tex:309 | matched at integer + RPY resolution on 94/100. The float fingerprint gate ($\varepsilon$=1e-4) failed | Proportion of episodes matching frozen right-arm pose at integer+RPY precision | Amendment 3 hold-in-place |
| M174 | methods_l2.tex:309 | on 94/100. The float fingerprint gate ($\varepsilon$=1e-4) failed on 17 episodes at $\approx$1e-4 | Tolerance epsilon for float fingerprint pairing verification | none |
| M175 | methods_l2.tex:310 | float fingerprint gate ($\varepsilon$=1e-4) failed on 17 episodes at $\approx$1e-4 drift because \texttt{trajectory[0]} | Number of episodes failing strict float fingerprint check | none |
| M176 | methods_l2.tex:310 | ($\varepsilon$=1e-4) failed on 17 episodes at $\approx$1e-4 drift because \texttt{trajectory[0]} is already one | Magnitude of numerical simulation float drift across episodes | none |
| M177 | methods_l2.tex:311 | drift because \texttt{trajectory[0]} is already one servo-step in and the scored (left) arm's | Step offset in simulation replay at index 0 | none |
| M178 | methods_l2.tex:319 | Three pre-registered diagnostics, each prediction committed before its | Number of pre-registered diagnostic analyses | none |
| M179 | methods_l2.tex:323 | Retrieval quality --- a cross-task correlate (n=2 tasks, not a within-task predictor).} | Number of tasks compared in cross-task correlation analysis | none |
| M180 | methods_l2.tex:325 | neighbours than L0a under an identical retriever (top-1 median 0.900 $\rightarrow$ 0.870, MW | Median top-1 retrieval cosine similarity shift from L0a (0.900) to L2 (0.870) | none |
| M181 | methods_l2.tex:326 | retriever (top-1 median 0.900 $\rightarrow$ 0.870, MW p=4.7e-17; top-3 0.883 $\rightarrow$ 0.827, | Mann-Whitney U test p-value for top-1 retrieval similarity difference | none |
| M182 | methods_l2.tex:326 | 0.870, MW p=4.7e-17; top-3 0.883 $\rightarrow$ 0.827, p=1.3e-26), consistent with a 5.5$\times$ | Mean/median top-3 retrieval cosine similarity shift from L0a (0.883) to L2 (0.827) | none |
| M183 | methods_l2.tex:326 | top-3 0.883 $\rightarrow$ 0.827, p=1.3e-26), consistent with a 5.5$\times$ thinner | Mann-Whitney U test p-value for top-3 retrieval similarity difference | none |
| M184 | methods_l2.tex:327 | p=1.3e-26), consistent with a 5.5$\times$ thinner buffer (547 vs 100 recaps, | Ratio of episodic buffer sizes between L0a and L2 | none |
| M185 | methods_l2.tex:327 | thinner buffer (547 vs 100 recaps, $\approx$28 usable left-aligned). Stated at the | Total recap count comparison (547 for L0a vs 100 for L2) | none |
| M186 | methods_l2.tex:327 | buffer (547 vs 100 recaps, $\approx$28 usable left-aligned). Stated at the level it | Count of usable left-arm aligned recaps in L2 buffer | none |
| M187 | methods_l2.tex:333 | Retrieval restores the teacher's round-1 bias.} Round-1 left-arm lateral bias $\Delta$X\_L (against | Episode round index for lateral bias probe | none |
| M188 | methods_l2.tex:335 | the L2-teacher's \emph{own} R1, not L0a's transplant): teacher $-$17.1, A\_ctrl\_rat (distilled) \textbf{$-$4.8}, | L2 teacher mean round-1 lateral bias $\Delta$X_L in grid units | none |
| M189 | methods_l2.tex:335 | transplant): teacher $-$17.1, A\_ctrl\_rat (distilled) \textbf{$-$4.8}, C\_retrieval \textbf{$-$17.2}. The pre-registered | Distilled A_ctrl_rat student mean round-1 lateral bias $\Delta$X_L in grid units | none |
| M190 | methods_l2.tex:336 | A\_ctrl\_rat (distilled) \textbf{$-$4.8}, C\_retrieval \textbf{$-$17.2}. The pre-registered $\sigma$ test did | C_retrieval student mean round-1 lateral bias $\Delta$X_L in grid units | none |
| M191 | methods_l2.tex:336 | test did not fire ($\sigma$ 15.5 vs 17.3, F=1.25 --- reported plainly); the | Standard deviation of round-1 lateral bias (15.5 for distilled vs 17.3 for retrieval) | none |
| M192 | methods_l2.tex:337 | ($\sigma$ 15.5 vs 17.3, F=1.25 --- reported plainly); the informative signal is | F-test statistic comparing variances of round-1 lateral bias | none |
| M193 | methods_l2.tex:338 | collapses to a magnitude-deficient prior ($\approx$28\% of teacher displacement), and the retrieval preamble | Ratio of distilled student displacement relative to teacher displacement | none |
| M194 | methods_l2.tex:340 | restores the teacher's magnitude almost exactly ($-$4.8 $\rightarrow$ $-$17.2 $\approx$ $-$17.1). This is the L2 analogue | Lateral displacement progression from distilled to retrieval vs teacher | none |
| M195 | methods_l2.tex:346 | the distilled arm's R1 sat on the teacher's ($-$16.7 $\approx$ $-$15.8); on L2 the distilled | L0a distilled student R1 (-16.7) vs teacher R1 (-15.8) in grid units | none |
| M196 | methods_l2.tex:346 | on L2 the distilled prior reaches only $-$4.8 against $-$17.1 ($\approx$72\% short). Training dose | L2 distilled student R1 (-4.8) vs L2 teacher R1 (-17.1) in grid units | none |
| M197 | methods_l2.tex:347 | prior reaches only $-$4.8 against $-$17.1 ($\approx$72\% short). Training dose is one candidate (L2's | Percentage shortfall of distilled student displacement relative to teacher | none |
| M198 | methods_l2.tex:348 | one candidate (L2's per-arm distillation saw 511 desirable rounds vs L0a's 992), suggesting | Comparison of training dose in desirable rounds between L2 (511) and L0a (992) | none |
| M199 | methods_l2.tex:351 | composition are confounded with dose at n=2, so no single cause is isolable. Labelled | Number of tasks compared in training dose analysis | none |
| M200 | methods_l2.tex:352 | no single cause is isolable. Labelled exploratory (n=2 tasks, a single before/after point, no dose-response | Number of tasks in exploratory cross-task analysis | none |
| M201 | methods_l2.tex:356 | match (surprise).} The +6 pp = 9 rescues (C\checkmark A$\times$) $-$ 3 regressions (A\checkmark C$\times$). Rescues share a | Arithmetic decomposition of net success rate change (+6 pp) into 9 rescues minus 3 regressions | none |
| M202 | methods_l2.tex:357 | init-pose signature: rescue init \texttt{dist\_red} mean 13.9 cm vs both-fail 21.6 cm (MW z=$-$3.88, | Mean initial distance to target for rescued episodes (13.9 cm) vs both-fail episodes (21.6 cm) | none |
| M203 | methods_l2.tex:358 | 13.9 cm vs both-fail 21.6 cm (MW z=$-$3.88, p=1e-4) --- retrieval rescues almost | Mann-Whitney test z-statistic for initial distance difference | none |
| M204 | methods_l2.tex:358 | both-fail 21.6 cm (MW z=$-$3.88, p=1e-4) --- retrieval rescues almost only episodes that | Mann-Whitney test p-value for initial distance difference | none |
| M205 | methods_l2.tex:360 | retrieval-similarity is \emph{not} higher (0.847 vs 0.868, p=0.03), so start distance, not | Mean retrieval similarity for rescued episodes (0.847) vs non-rescued episodes (0.868) | none |
| M206 | methods_l2.tex:360 | is \emph{not} higher (0.847 vs 0.868, p=0.03), so start distance, not match quality, | p-value for retrieval similarity difference | none |
| M207 | methods_l2.tex:365 | correction, (b)) and in \textbf{direction} (+6 pp), but its conversion to end-task success | Net success rate difference direction and point estimate | none |
| M208 | methods_l2.tex:366 | retrieved correction is injected \textbf{once per episode} (anchored on \texttt{init\_L\_EE}, round-0 only | Injection frequency of memory correction per episode | none |
| M209 | methods_l2.tex:367 | \textbf{once per episode} (anchored on \texttt{init\_L\_EE}, round-0 only --- verified literal, not metaphor), | Episode round index where initial memory preamble is anchored | none |
| M210 | methods_l2.tex:370 | already within reach of the 0.05 m gate (c). Far-start episodes fire the | Reach success tolerance gate distance in meters | none |
| M211 | methods_l2.tex:371 | The effect is therefore \textbf{small (+6 pp, n.s.), not absent.} Two levels, kept | Summary effect size of retrieval intervention | none |
| M212 | methods_l2.tex:373 | not rescue'' objection: \emph{between tasks} (a, n=2) thinner buffer co-occurs with a smaller | Number of tasks compared | none |
| M213 | methods_l2.tex:380 | gap-to-teacher basis, L0a retrieval closed $\approx$99\% of the parity gap (34.0 of | Proportion of parity gap to teacher closed by retrieval in L0a | none |
| M214 | methods_l2.tex:381 | $\approx$99\% of the parity gap (34.0 of 34.3 pp, A\_ctrl\_rat 15\% $\rightarrow$ teacher | Gain in percentage points (34.0 pp) relative to total parity gap (34.3 pp) in L0a | none |
| M215 | methods_l2.tex:381 | gap (34.0 of 34.3 pp, A\_ctrl\_rat 15\% $\rightarrow$ teacher 49.3\%); \textbf{L2 retrieval | L0a bare adapter (A_ctrl_rat) baseline success rate | none |
| M216 | methods_l2.tex:381 | 34.3 pp, A\_ctrl\_rat 15\% $\rightarrow$ teacher 49.3\%); \textbf{L2 retrieval closes 42.9\%} of | L0a teacher success rate | none |
| M217 | methods_l2.tex:381 | 15\% $\rightarrow$ teacher 49.3\%); \textbf{L2 retrieval closes 42.9\%} of the per-arm gap (A\_ctrl\_rat 14\% | Proportion of per-arm parity gap to teacher recovered by retrieval in L2 | per_arm_rescore.json |
| M218 | methods_l2.tex:382 | closes 42.9\%} of the per-arm gap (A\_ctrl\_rat 14\% $\rightarrow$ L2 per-arm teacher \textbf{28.0\%}, | L2 bare adapter (A_ctrl_rat) baseline per-arm success rate | per_arm_rescore.json |
| M219 | methods_l2.tex:382 | 14\% $\rightarrow$ L2 per-arm teacher \textbf{28.0\%}, pinned from \texttt{per\_arm\_rescore.json}; headroom 14 | L2 teacher per-arm success rate benchmark | per_arm_rescore.json |
| M220 | methods_l2.tex:383 | pinned from \texttt{per\_arm\_rescore.json}; headroom 14 pp, +6 pp recovered = 6/14). This | Total available headroom between baseline (14%) and teacher (28.0%) in percentage points | per_arm_rescore.json |
| M221 | methods_l2.tex:383 | \texttt{per\_arm\_rescore.json}; headroom 14 pp, +6 pp recovered = 6/14). This framing is \textbf{post-hoc | Success rate points recovered (6 pp) out of 14 pp headroom | per_arm_rescore.json |
| M222 | methods_l2.tex:384 | after the raw SR was known); pinning the 28.0\% denominator removes the ``$\approx$'', not the | Pinned denominator value for teacher per-arm success rate | per_arm_rescore.json |
| M223 | methods_l2.tex:386 | not the exploratory label, and the raw +6 pp n.s. is always reported alongside. | Raw unnormalized effect size of L2 retrieval contrast | none |
| M224 | methods_l2.tex:404 | by label not directory (verify-layer 2/2) & l2\_amendment\_2.md \\ L2-2 add | Verify-layer interception success count across program | l2_amendment_2.md |
| M225 | methods_l2.tex:405 | rollback + arch byte-patch (verify-layer 3/3) & l2\_amendment\_2.md \\ L2-3 & | Verify-layer interception success count across program | l2_amendment_2.md |
| M226 | methods_l2.tex:406 | non-scored arm frozen; left-scored $\times$2 protocols n=100, seed 4600; position-only | Protocol multiplier count (2 protocols) | l2_amendment_3.md |
| M227 | methods_l2.tex:406 | arm frozen; left-scored $\times$2 protocols n=100, seed 4600; position-only success; format-contract | Sample size per protocol | l2_amendment_3.md |
| M228 | methods_l2.tex:406 | $\times$2 protocols n=100, seed 4600; position-only success; format-contract gate (verify-layer | Base random seed for evaluation | l2_amendment_3.md |
| M229 | methods_l2.tex:406 | position-only success; format-contract gate (verify-layer 4/4) & l2\_amendment\_3.md (\texttt{96e1388}; spec-implementing code | Verify-layer cumulative interception success count | l2_amendment_3.md |
| M230 | methods_l2.tex:411 | eval number existed --- the Step-8 eval crashed at episode~1 on a missing | Pipeline execution step index | none |
| M231 | methods_l2.tex:412 | --- the Step-8 eval crashed at episode~1 on a missing prompt template, so the | Episode index where evaluation script failed | none |
| M232 | related_work.tex:49 | fold experience \emph{into weights}: RECAP / $\pi^{*}_{0.6}$~\citep{pistar06_2025} learns from experience via advantage-conditioned | Prior algorithm/model variant with parameter subscript 0.6 | \citep{pistar06_2025} |
| M233 | related_work.tex:70 | self-produced rationale at inference did not help ($+1$ pp) while retrieved content did ($+23$ pp) | Performance difference in success rate from self-produced rationale at inference (B_main vs A_action_only) | none |
| M234 | related_work.tex:70 | help ($+1$ pp) while retrieved content did ($+23$ pp) --- qualifies when rationale externalisation pays. | Performance difference in success rate from retrieved content (C_retrieval vs B_main) | none |
| M235 | appendix_amendments.tex:11 | with the Methods: the D11 amendments (1--14) in Appendix~A1 (Amendment 15, 2026-10-05, | Range and count of pre-registration amendments for D11 study | none |
| M236 | appendix_amendments.tex:11 | (1--14) in Appendix~A1 (Amendment 15, 2026-10-05, registers inference-only reinforcement arms that | Post-study amendment identifier/number | none |
| M237 | appendix_amendments.tex:13 | post-date the D11 results; Amendment 16, 2026-10-05, \texttt{730b9fc}, is a documentation-only | Documentation erratum amendment number | \texttt{730b9fc} |
| M238 | appendix_amendments.tex:16 | Experiment-1 Methods (\S3), and the L2 amendments (1/1a/2/3) in the table at the end | List of L2 pre-registration amendment identifiers | none |
| M239 | appendix_teacher_provenance.tex:8 | \texttt{server/llama\_server\_teacher.sh} carried \texttt{--reasoning-budget 512} unchanged from commit \texttt{a2aebb9} (2026-06-08) | Output token budget allocated for teacher VLM reasoning mode | commit \texttt{a2aebb9} |
| M240 | appendix_teacher_provenance.tex:11 | collect (2026-07-14). Same binary, same model (gemma-4-31B-it Q4\_K\_M), same mmproj, same ctx-size | Parameter count of teacher base model (31 billion parameters) | none |
| M241 | appendix_teacher_provenance.tex:11 | binary, same model (gemma-4-31B-it Q4\_K\_M), same mmproj, same ctx-size 16384, | 4-bit medium k-quant quantization format of teacher model | none |
| M242 | appendix_teacher_provenance.tex:12 | Q4\_K\_M), same mmproj, same ctx-size 16384, same \texttt{--parallel 1}. | Server context window token length limit | none |
| M243 | appendix_teacher_provenance.tex:12 | same ctx-size 16384, same \texttt{--parallel 1}. \subsection*{The delta is task, not | Server concurrent request processing slot count | none |
| M244 | appendix_teacher_provenance.tex:17 | \textbf{D10 (L0a-Left, single-arm):} inline Stage-4 recap generation succeeded almost completely --- | Training pipeline stage index | none |
| M245 | appendix_teacher_provenance.tex:21 | teacher-server connection outages (recaps\_d10 = 547 records total across 7 runs). | Total count of episodic memory records in D10 collect buffer | none |
| M246 | appendix_teacher_provenance.tex:21 | (recaps\_d10 = 547 records total across 7 runs). \item \textbf{L2 (dual-push) first | Number of teacher collection runs contributing to D10 buffer | none |
| M247 | appendix_teacher_provenance.tex:22 | first collect:} inline recap failed 8/8 episodes, every one ``Empty content in VLM | Proportion/count of initial L2 collect episodes failing recap generation | none |
| M248 | appendix_teacher_provenance.tex:28 | reasoning mode, enabled by \texttt{--reasoning-budget 512}, can consume the entire 400-token | Teacher reasoning mode token budget | none |
| M249 | appendix_teacher_provenance.tex:28 | 512}, can consume the entire 400-token output budget on \texttt{reasoning\_content} and return | Maximum output token generation limit in llama.cpp server | none |
| M250 | appendix_teacher_provenance.tex:38 | Teacher relaunched with \texttt{--reasoning off --reasoning-budget 0} (commit \texttt{cabab3c}). Verified: the | Token budget allocated to reasoning mode when disabled | commit \texttt{cabab3c} |
| M251 | appendix_teacher_provenance.tex:40 | call that returned empty now returns a real 469-char lesson in 7 s. Reasoning-off | Character length of generated lesson text | none |
| M252 | appendix_teacher_provenance.tex:40 | now returns a real 469-char lesson in 7 s. Reasoning-off is safe for L0a | Elapsed time duration in seconds for recap generation | none |
| M253 | appendix_teacher_provenance.tex:41 | for L0a too (D10 succeeded on 512 precisely because it never needed the reasoning | Teacher reasoning token budget | none |
| M254 | appendix_teacher_provenance.tex:46 | (L0a) recaps were generated \textbf{reasoning-on (budget 512)}. \item L2 recaps are generated | Token budget allocated for reasoning during D10 recap generation | none |
| M255 | appendix_teacher_provenance.tex:47 | \item L2 recaps are generated \textbf{reasoning-off (budget 0)}. \item This is a teacher-config | Token budget allocated for reasoning during L2 recap generation | none |
| M256 | appendix_teacher_provenance.tex:53 | buffers are ever compared directly. \item Stage-1 reasoning quality may differ subtly under reasoning-off | Training pipeline stage index | none |
| M257 | appendix_teacher_provenance.tex:54 | differ subtly under reasoning-off vs reasoning-on. D10's Stage-1 ran reasoning-on; if a clean | Training pipeline stage index | none |
| M258 | appendix_teacher_provenance.tex:63 | \item D10 / L0a teacher: gemma-4-31B Q4\_K\_M, ctx 16384, \textbf{reasoning-budget | Parameter count of teacher model (31B parameters) | none |
| M259 | appendix_teacher_provenance.tex:63 | D10 / L0a teacher: gemma-4-31B Q4\_K\_M, ctx 16384, \textbf{reasoning-budget 512}. | Quantization format of teacher model | none |
| M260 | appendix_teacher_provenance.tex:63 | teacher: gemma-4-31B Q4\_K\_M, ctx 16384, \textbf{reasoning-budget 512}. \item L2 | Teacher context window size in tokens | none |
| M261 | appendix_teacher_provenance.tex:63 | Q4\_K\_M, ctx 16384, \textbf{reasoning-budget 512}. \item L2 teacher (from 2026-07-14): | Teacher reasoning token budget | none |
| M262 | appendix_teacher_provenance.tex:64 | (from 2026-07-14): same, \textbf{reasoning off / budget 0}. \item Delta: reasoning off; forced | Teacher reasoning token budget | none |
