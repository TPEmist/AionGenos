# Pre-Publication Audit: Quantitative Claims Inventory

- **Audit Task:** TASK A1-workshop
- **Audited Tree:** `/home/control/audit/fab376a` (SHA `fab376a`)
- **Audited Document:** `/home/control/audit/fab376a/docs/paper/bar/main.tex`
- **Total Quantitative Claims:** 142 (Prose/Tables/Captions: 123, Figures: 19)

| id | file:line | exact literal (verbatim, including surrounding 8 words) | what it measures (one phrase) | any cited source in the text (amendment, log, script) or 'none' |
|---|---|---|---|---|
| W1 | docs/paper/bar/main.tex:58 | task. Behavioural distillation (one SFT + KTO round into LoRA weights) of | number of behavioural distillation training rounds | none |
| W2 | docs/paper/bar/main.tex:59-60 | the memory benefit ($+1$ pp over an action-only control, | confirmatory advantage of distilled memory teacher over action-only control | none |
| W3 | docs/paper/bar/main.tex:64 | weights recovered it ($+34$ pp on identical weights, $z{=}5.15$, | exploratory SR gain from retrieval on identical student weights | none |
| W4 | docs/paper/bar/main.tex:64 | pp on identical weights, $z{=}5.15$, exploratory; $+23$ pp | two-proportion z-statistic for identical-weights retrieval contrast | none |
| W5 | docs/paper/bar/main.tex:65 | identical weights, $z{=}5.15$, exploratory; $+23$ pp on the pre-registered protocol | confirmatory SR gain of retrieval vs pre-registered distilled protocol contrast (B_main) | none |
| W6 | docs/paper/bar/main.tex:65 | the pre-registered protocol contrast, $z{=}3.36$, confirmatory; $+36$ / | two-proportion z-statistic for pre-registered protocol contrast | none |
| W7 | docs/paper/bar/main.tex:66 | protocol contrast, $z{=}3.36$, confirmatory; $+36$ / $+29$ pp under | auto-reset sensitivity SR gain for identical-weights retrieval contrast | none |
| W8 | docs/paper/bar/main.tex:66 | $z{=}3.36$, confirmatory; $+36$ / $+29$ pp under a pre-registered auto-reset | auto-reset sensitivity SR gain for pre-registered protocol contrast | none |
| W9 | docs/paper/bar/main.tex:67 | pooled memory-teacher reference (49.3\%). An exploratory probe | pooled success rate of memory-augmented teacher reference | none |
| W10 | docs/paper/bar/main.tex:72 | is not significant ($+6$ pp, sub-MDE). Follow-up controls | retrieval advantage on second, harder reach task | none |
| W11 | docs/paper/bar/main.tex:74 | with no adapter (48\%) and every other | success rate of base model with buffer and no adapter | none |
| W12 | docs/paper/bar/main.tex:74 | every other adapter (53--55\%) alike: the recipe | success rate range of other three adapters with buffer | none |
| W13 | docs/paper/bar/main.tex:104 | targets vary in a $2{\times}2$ over the teacher's native | factorial design of distillation targets (thought x gist) | Table 1 (Table~\ref{tab:arms}) |
| W14 | docs/paper/bar/main.tex:128 | only & none & 25 (21) \\ \texttt{A\_ctrl\_rat} & | as-run success count (out of 100) for arm A_action_only | Amendment 15, pin 8 |
| W15 | docs/paper/bar/main.tex:128 | & none & 25 (21) \\ \texttt{A\_ctrl\_rat} & + | auto-reset sensitivity success count (out of 100) for arm A_action_only | Amendment 15, pin 8 |
| W16 | docs/paper/bar/main.tex:129 | thought & none & 15 (12) \\ \texttt{D\_gist} & | as-run success count (out of 100) for arm A_ctrl_rat | Amendment 15, pin 8 |
| W17 | docs/paper/bar/main.tex:129 | & none & 15 (12) \\ \texttt{D\_gist} & + | auto-reset sensitivity success count (out of 100) for arm A_ctrl_rat | Amendment 15, pin 8 |
| W18 | docs/paper/bar/main.tex:130 | gist & none & 19 (17) \\ \texttt{B\_main} & | as-run success count (out of 100) for arm D_gist | Amendment 15, pin 8 |
| W19 | docs/paper/bar/main.tex:130 | & none & 19 (17) \\ \texttt{B\_main} & + | auto-reset sensitivity success count (out of 100) for arm D_gist | Amendment 15, pin 8 |
| W20 | docs/paper/bar/main.tex:131 | gist & none & 26 (19) \\ \texttt{C\_retrieval} & | as-run success count (out of 100) for arm B_main | Amendment 15, pin 8 |
| W21 | docs/paper/bar/main.tex:131 | & none & 26 (19) \\ \texttt{C\_retrieval} & (= | auto-reset sensitivity success count (out of 100) for arm B_main | Amendment 15, pin 8 |
| W22 | docs/paper/bar/main.tex:132 | frozen teacher buffer & 49 (48) \\ \bottomrule \end{tabular} | as-run success count (out of 100) for arm C_retrieval | Amendment 15, pin 8 |
| W23 | docs/paper/bar/main.tex:132 | teacher buffer & 49 (48) \\ \bottomrule \end{tabular} \caption{The | auto-reset sensitivity success count (out of 100) for arm C_retrieval | Amendment 15, pin 8 |
| W24 | docs/paper/bar/main.tex:135 | \\ \bottomrule \end{tabular} \caption{The five evaluation arms. The four distilled | total number of evaluation arms evaluated | none |
| W25 | docs/paper/bar/main.tex:135 | five evaluation arms. The four distilled arms share one pinned batch | count of student arms trained via distillation | none |
| W26 | docs/paper/bar/main.tex:137 | distillation \emph{target} contains (a $2{\times}2$ over teacher's native thought | factorial design of distillation targets (thought x gist) | none |
| W27 | docs/paper/bar/main.tex:141 | inference. SR = as-run successes of 100 (primary); in parentheses the | evaluation sample size per arm (episodes) | none |
| W28 | docs/paper/bar/main.tex:143 | reached before an inherited 24\,s environment auto-reset (\S4).} \label{tab:arms} | environment auto-reset timeout duration in seconds | none |
| W29 | docs/paper/bar/main.tex:176 | an action-only control by $+1$ pp (n.s., confirmatory; sensitivity $-2$ | confirmatory advantage of distilled memory teacher over action-only control | none |
| W30 | docs/paper/bar/main.tex:176 | pp (n.s., confirmatory; sensitivity $-2$ pp); the registered test | auto-reset sensitivity advantage of distilled memory teacher over action-only control | none |
| W31 | docs/paper/bar/main.tex:181 | attaching inference-time retrieval added $+34$ pp (identical-weights contrast, $z{=}5.15$, exploratory; | exploratory SR gain from retrieval on identical student weights | none |
| W32 | docs/paper/bar/main.tex:182 | $+34$ pp (identical-weights contrast, $z{=}5.15$, exploratory; sensitivity $+36$ | two-proportion z-statistic for identical-weights retrieval contrast | none |
| W33 | docs/paper/bar/main.tex:182 | contrast, $z{=}5.15$, exploratory; sensitivity $+36$ pp); the pre-registered protocol | auto-reset sensitivity SR gain for identical-weights retrieval contrast | none |
| W34 | docs/paper/bar/main.tex:183 | protocol contrast agrees at $+23$ pp ($z{=}3.36$, confirmatory; sensitivity $+29$ | confirmatory SR gain of retrieval vs pre-registered distilled protocol contrast (B_main) | none |
| W35 | docs/paper/bar/main.tex:183 | at $+23$ pp ($z{=}3.36$, confirmatory; sensitivity $+29$ | two-proportion z-statistic for pre-registered protocol contrast | none |
| W36 | docs/paper/bar/main.tex:184 | pp ($z{=}3.36$, confirmatory; sensitivity $+29$ pp). Retrieval reached the | auto-reset sensitivity SR gain for pre-registered protocol contrast | none |
| W37 | docs/paper/bar/main.tex:185 | pooled memory-teacher reference (Figure~\ref{fig:sr}; 49.3\%, 109/221 over three | pooled success rate of memory-augmented teacher reference | Figure 1 (Figure~\ref{fig:sr}) |
| W38 | docs/paper/bar/main.tex:185 | memory-teacher reference (Figure~\ref{fig:sr}; 49.3\%, 109/221 over three unseeded collect | pooled raw successes over total episodes across three collect runs | none |
| W39 | docs/paper/bar/main.tex:185-186 | (Figure~\ref{fig:sr}; 49.3\%, 109/221 over three unseeded collect runs, not seed-matched to | number of unseeded collect runs pooled for teacher reference | none |
| W40 | docs/paper/bar/main.tex:187 | to the evaluation; sensitivity 47.5\%). \textbf{Which baseline the | auto-reset sensitivity success rate of pooled memory teacher reference | none |
| W41 | docs/paper/bar/main.tex:191 | bare success rate (15/100; sensitivity 12) is | as-run success rate of arm A_ctrl_rat (bare student) | Table 1 (Table~\ref{tab:arms}) |
| W42 | docs/paper/bar/main.tex:191 | bare success rate (15/100; sensitivity 12) is the lowest | auto-reset sensitivity success count (out of 100) for arm A_ctrl_rat | none |
| W43 | docs/paper/bar/main.tex:191 | the lowest of the four distilled arms. The $+34$ pp | total number of distilled student arms | none |
| W44 | docs/paper/bar/main.tex:192 | four distilled arms. The $+34$ pp identical-weights contrast is therefore | exploratory SR gain from retrieval on identical student weights | none |
| W45 | docs/paper/bar/main.tex:194 | against the strongest (\texttt{B\_main}, 26/100; sensitivity 19) gives | as-run success rate of arm B_main | none |
| W46 | docs/paper/bar/main.tex:194 | the strongest (\texttt{B\_main}, 26/100; sensitivity 19) gives the more | auto-reset sensitivity success count (out of 100) for arm B_main | none |
| W47 | docs/paper/bar/main.tex:194 | gives the more conservative $+23$ pp. We report both. | confirmatory SR gain of retrieval vs B_main | none |
| W48 | docs/paper/bar/main.tex:195 | adapter and on the other three adapters is reported in \S4. | count of additional adapters tested with retrieval buffer | \S4 |
| W49 | docs/paper/bar/main.tex:201 | \centering \includegraphics[width=0.66\linewidth]{qual_sr_bars.png} \caption{As-run success (of 100) for all five arms; | evaluation sample size per arm (episodes) | none |
| W50 | docs/paper/bar/main.tex:201 | success (of 100) for all five arms; no confidence intervals | total number of evaluation arms shown | none |
| W51 | docs/paper/bar/main.tex:202 | intervals are drawn. The four weight-substrate arms (grey; only \texttt{D\_gist} and | count of weight-substrate arms evaluated | none |
| W52 | docs/paper/bar/main.tex:204 | in their targets) span 15--26; memory supplied in | range of as-run success rates across four weight-substrate arms | none |
| W53 | docs/paper/bar/main.tex:206 | pooled memory-teacher reference (dashed, 49.3\%, three unseeded collect | pooled success rate of memory-augmented teacher reference | none |
| W54 | docs/paper/bar/main.tex:206 | memory-teacher reference (dashed, 49.3\%, three unseeded collect runs, not seed-matched). \texttt{A\_ctrl\_rat} | number of unseeded collect runs pooled for teacher reference | none |
| W55 | docs/paper/bar/main.tex:213 | pre-registered per-arm predictions; Figure~\ref{fig:r1}).} Round-1 lateral displacement, in scalar-guard | index of reasoning/action round analyzed for mechanism probe | none |
| W56 | docs/paper/bar/main.tex:214 | scalar-guard grid units (1 unit $=$ 0.45\,cm along x; units erratum, | physical length conversion factor along x per scalar-guard grid unit | Amendment 16 |
| W57 | docs/paper/bar/main.tex:217 | of situation (per-arm means $-15.8$ to $-18.1$, near the memory-teacher | range of per-arm mean round-1 lateral displacements (grid units) across distilled arms | none |
| W58 | docs/paper/bar/main.tex:218 | near the memory-teacher fingerprint $-15.8$) --- but not | reference memory-teacher round-1 lateral displacement fingerprint (grid units) | none |
| W59 | docs/paper/bar/main.tex:220 | mean toward zero ($-7.1$) with a wider, | mean round-1 lateral displacement (grid units) under retrieval on fixed weights (C_retrieval) | none |
| W60 | docs/paper/bar/main.tex:220 | wider, per-episode spread ($\sigma$ $14.4$ vs $7.9$--$10.1$). This selects | standard deviation of round-1 lateral displacement (grid units) for C_retrieval | none |
| W61 | docs/paper/bar/main.tex:221 | spread ($\sigma$ $14.4$ vs $7.9$--$10.1$). This selects the | range of standard deviations of round-1 lateral displacement (grid units) across distilled arms | none |
| W62 | docs/paper/bar/main.tex:228 | \begin{figure}[t] \centering \includegraphics[width=0.7\linewidth]{fig2_r1_dx.png} \caption{Round-1 $\Delta$X (grid units; 1 | index of reasoning/action round analyzed in Figure 2 | none |
| W63 | docs/paper/bar/main.tex:228 | \caption{Round-1 $\Delta$X (grid units; 1 unit $=$ 0.45\,cm along x), mean $\pm$ | physical length conversion factor along x per scalar-guard grid unit | none |
| W64 | docs/paper/bar/main.tex:232 | D6 memoryless teacher ($-23.5$) and the memory | reference round-1 lateral displacement fingerprint (grid units) for D6 memoryless teacher | none |
| W65 | docs/paper/bar/main.tex:233 | teacher's last quartile ($-15.8$). The four distilled | reference round-1 lateral displacement fingerprint (grid units) for memory teacher last quartile | none |
| W66 | docs/paper/bar/main.tex:233 | last quartile ($-15.8$). The four distilled arms cluster on one static | count of distilled arms plotted in Figure 2 | none |
| W67 | docs/paper/bar/main.tex:241 | \label{fig:r1} \end{figure} \section{Reviewer-requested controls} Three controls requested in review were | number of reviewer-requested control experiments | Amendment 15 |
| W68 | docs/paper/bar/main.tex:243 | run on the same 100 seeded configurations with the frozen buffer | sample size of evaluation configurations (episodes) per control arm | none |
| W69 | docs/paper/bar/main.tex:246 | main evaluation, so the two-proportion $z$ is primary by the | statistical test specification for reviewer-requested controls | none |
| W70 | docs/paper/bar/main.tex:246 | the locked fallback ($\alpha{=}0.05$). Auto-reset sensitivity counts | significance level threshold for locked two-proportion z fallback test | none |
| W71 | docs/paper/bar/main.tex:250 | and \emph{no} adapter scored 48 (48) of 100, against 49 (48) | as-run SR (48) and sensitivity SR (48) out of 100 for base model with buffer and no adapter | none |
| W72 | docs/paper/bar/main.tex:250 | (48) of 100, against 49 (48) for \texttt{C\_retrieval}: $-1$ pp, | as-run SR (49) and sensitivity SR (48) out of 100 for C_retrieval in control contrast | none |
| W73 | docs/paper/bar/main.tex:251 | 49 (48) for \texttt{C\_retrieval}: $-1$ pp, 95\% CI $[-14.6, | difference in SR between base model without adapter and C_retrieval | none |
| W74 | docs/paper/bar/main.tex:251 | for \texttt{C\_retrieval}: $-1$ pp, 95\% CI $[-14.6, +12.6]$, $z{=}{-}0.14$, $p{=}0.89$. | confidence level of confidence interval for base vs C_retrieval difference | none |
| W75 | docs/paper/bar/main.tex:251 | $-1$ pp, 95\% CI $[-14.6, +12.6]$, $z{=}{-}0.14$, $p{=}0.89$. This | 95% confidence interval (percentage points) for base vs C_retrieval difference | none |
| W76 | docs/paper/bar/main.tex:251 | 95\% CI $[-14.6, +12.6]$, $z{=}{-}0.14$, $p{=}0.89$. This misses | two-proportion z-statistic for base model vs C_retrieval | none |
| W77 | docs/paper/bar/main.tex:252 | CI $[-14.6, +12.6]$, $z{=}{-}0.14$, $p{=}0.89$. This misses the | p-value of two-proportion z-test for base model vs C_retrieval | none |
| W78 | docs/paper/bar/main.tex:255 | one of up to 14.6 pp), so by the | upper bound of non-excluded adapter contribution magnitude | none |
| W79 | docs/paper/bar/main.tex:259 | same buffer on the other three adapters gave 53 (53) for | number of additional adapters evaluated with retrieval buffer | none |
| W80 | docs/paper/bar/main.tex:259 | other three adapters gave 53 (53) for \texttt{A\_action\_only}, 53 (50) | as-run SR (53) and sensitivity SR (53) out of 100 for A_action_only with buffer | none |
| W81 | docs/paper/bar/main.tex:259 | 53 (53) for \texttt{A\_action\_only}, 53 (50) for \texttt{B\_main} and 55 | as-run SR (53) and sensitivity SR (50) out of 100 for B_main with buffer | none |
| W82 | docs/paper/bar/main.tex:260 | (50) for \texttt{B\_main} and 55 (55) for \texttt{D\_gist}, up from | as-run SR (55) and sensitivity SR (55) out of 100 for D_gist with buffer | none |
| W83 | docs/paper/bar/main.tex:260-261 | for \texttt{D\_gist}, up from 25, 26 and 19 without it ($+28$, $+27$ | baseline un-retrieved SRs for A_action_only (25), B_main (26), and D_gist (19) | none |
| W84 | docs/paper/bar/main.tex:261 | 19 without it ($+28$, $+27$ and $+36$ | retrieval SR gain (percentage points) for A_action_only | none |
| W85 | docs/paper/bar/main.tex:261 | 19 without it ($+28$, $+27$ and $+36$ pp; $z{=}4.06$, | retrieval SR gain (percentage points) for B_main | none |
| W86 | docs/paper/bar/main.tex:261 | it ($+28$, $+27$ and $+36$ pp; $z{=}4.06$, $3.91$, $5.27$; | retrieval SR gain (percentage points) for D_gist | none |
| W87 | docs/paper/bar/main.tex:261 | $+27$ and $+36$ pp; $z{=}4.06$, $3.91$, $5.27$; all | two-proportion z-statistic for A_action_only retrieval gain | none |
| W88 | docs/paper/bar/main.tex:261 | and $+36$ pp; $z{=}4.06$, $3.91$, $5.27$; all $p<10^{-4}$). | two-proportion z-statistic for B_main retrieval gain | none |
| W89 | docs/paper/bar/main.tex:261 | $+36$ pp; $z{=}4.06$, $3.91$, $5.27$; all $p<10^{-4}$). All | two-proportion z-statistic for D_gist retrieval gain | none |
| W90 | docs/paper/bar/main.tex:262 | $z{=}4.06$, $3.91$, $5.27$; all $p<10^{-4}$). All three land | p-value bound for retrieval gains across the three adapters | none |
| W91 | docs/paper/bar/main.tex:262 | $3.91$, $5.27$; all $p<10^{-4}$). All three land in the registered | count of adapter control arms landing in teacher band | none |
| W92 | docs/paper/bar/main.tex:262 | registered teacher band (45--55\%), and none differs | target success rate range defining registered teacher band | none |
| W93 | docs/paper/bar/main.tex:263 | differs from \texttt{C\_retrieval} ($\|\Delta\|\le 6$ pp, $p\ge 0.39$). The | maximum absolute difference in SR between adapter controls and C_retrieval | none |
| W94 | docs/paper/bar/main.tex:264 | \texttt{C\_retrieval} ($\|\Delta\|\le 6$ pp, $p\ge 0.39$). The $+34$ pp | minimum p-value for contrasts between adapter controls and C_retrieval | none |
| W95 | docs/paper/bar/main.tex:264 | pp, $p\ge 0.39$). The $+34$ pp is therefore not specific | exploratory SR gain from retrieval on identical student weights | none |
| W96 | docs/paper/bar/main.tex:267 | cost.} Measured back-to-back on one server, 20 steps per | count of hardware servers used for benchmark | none |
| W97 | docs/paper/bar/main.tex:267-268 | back-to-back on one server, 20 steps per protocol, the teacher, the | sample size of evaluation steps per protocol for cost profiling | none |
| W98 | docs/paper/bar/main.tex:269 | student with retrieval generate 207 / 186 / 220 completion tokens and take 14.1 / | completion tokens per step generated by teacher, student, and student with retrieval | none |
| W99 | docs/paper/bar/main.tex:269-270 | completion tokens and take 14.1 / 11.2 / 13.7 s per step: the same order. | inference latency (seconds per step) for teacher, student, and student with retrieval | none |
| W100 | docs/paper/bar/main.tex:280 | to this recipe (single-round SFT + composable-KTO, LoRA | number of training rounds in distillation recipe | none |
| W101 | docs/paper/bar/main.tex:281 | SFT + composable-KTO, LoRA rank-16), task, and data | LoRA adapter bottleneck rank | none |
| W102 | docs/paper/bar/main.tex:285 | not reach significance ($+6$ pp, confirmatory contrast on | confirmatory retrieval advantage on second, harder reach task | none |
| W103 | docs/paper/bar/main.tex:286 | metric promoted post hoc, 95\% CI $[-4.5, +16.4]$, sub-MDE; auto-reset | confidence level of confidence interval for second task retrieval effect | none |
| W104 | docs/paper/bar/main.tex:286 | post hoc, 95\% CI $[-4.5, +16.4]$, sub-MDE; auto-reset sensitivity | 95% confidence interval (percentage points) for second task retrieval effect | none |
| W105 | docs/paper/bar/main.tex:288 | diagnostics show a direction-consistent round-1 shift (the registered $\sigma$ | index of reasoning/action round analyzed in second task diagnostics | none |
| W106 | docs/paper/bar/main.tex:289 | round-1 shift (the registered $\sigma$ test did not fire) and | pre-registered variance test of round-1 lateral displacement for second task | none |
| W107 | docs/paper/bar/main.tex:301 | suite would require. \paragraph{Limitations.} One training run per arm. The spread across | number of training runs performed per experimental arm | none |
| W108 | docs/paper/bar/main.tex:302 | The spread across the four distilled arms (15--26\%, i.e.\ 11 pp) | total number of distilled student arms | none |
| W109 | docs/paper/bar/main.tex:302 | four distilled arms (15--26\%, i.e.\ 11 pp) | range of success rates across four distilled arms | none |
| W110 | docs/paper/bar/main.tex:302 | distilled arms (15--26\%, i.e.\ 11 pp) exceeds the $+10$ | spread in success rate across the four distilled arms | none |
| W111 | docs/paper/bar/main.tex:302 | 11 pp) exceeds the $+10$ pp minimum effect T1 was | minimum detectable effect size registered for hypothesis test T1 | T1 registration |
| W112 | docs/paper/bar/main.tex:304 | is not one the $2{\times}2$ predicts --- both single-factor | factorial design of distillation targets (thought x gist) | none |
| W113 | docs/paper/bar/main.tex:306-307 | explain this, but with one run per arm it is untested; it | number of training runs conducted per arm | none |
| W114 | docs/paper/bar/main.tex:310 | the same adapter with no second training run between them, so the | absence of additional training runs between compared arms | none |
| W115 | docs/paper/bar/main.tex:310 | between them, so the $+34$ pp cannot be a training-run | exploratory SR gain from retrieval on identical student weights | none |
| W116 | docs/paper/bar/main.tex:311 | control (\S4) is a single run. One task family, | number of evaluation runs conducted per adapter control | \S4 |
| W117 | docs/paper/bar/main.tex:311 | is a single run. One task family, in simulation. Teacher | number of task families evaluated | none |
| W118 | docs/paper/bar/main.tex:313-314 | the same order for all three protocols (\S4). Two instrument defects | number of protocols compared in cost profiling | \S4 |
| W119 | docs/paper/bar/main.tex:314 | all three protocols (\S4). Two instrument defects are disclosed. An inherited | count of disclosed instrument defects in experimental setup | none |
| W120 | docs/paper/bar/main.tex:314 | are disclosed. An inherited 24\,s environment auto-reset lets long | environment auto-reset timeout duration in seconds | none |
| W121 | docs/paper/bar/main.tex:318-319 | instruction field of all 547 buffer entries but in none of | total number of entries in the frozen experience buffer | none |
| W122 | docs/paper/bar/main.tex:319 | the retrieved lessons (517/547 name the colour); retrieval | fraction of buffer lessons explicitly naming the target colour | none |
| W123 | docs/paper/bar/main.tex:322 | this study, and the two routes deliver the buffer in | number of routes compared for delivering experience buffer (distillation vs retrieval) | none |
| W124 | docs/paper/bar/main.tex:200 (\includegraphics{qual_sr_bars.png}) | identical weights, retrieval toggled: 15 → 49 | SR comparison between bare weights (15) and retrieval (49) | none (no generating script named in main.tex comments; MANIFEST.md names scripts/figures/make_qualitative_figs.py) |
| W125 | docs/paper/bar/main.tex:200 (\includegraphics{qual_sr_bars.png}) | Success rate (n / 100) | sample size denominator per evaluation arm | none (no generating script named in main.tex comments; MANIFEST.md names scripts/figures/make_qualitative_figs.py) |
| W126 | docs/paper/bar/main.tex:200 (\includegraphics{qual_sr_bars.png}) | pooled memory-teacher reference 49.3% (not seed-matched) | reference success rate of pooled memory-augmented teacher | none (no generating script named in main.tex comments; MANIFEST.md names scripts/figures/make_qualitative_figs.py) |
| W127 | docs/paper/bar/main.tex:200 (\includegraphics{qual_sr_bars.png}) | A_action_only bar label: 25/100 | as-run success count out of 100 for A_action_only | none (no generating script named in main.tex comments; MANIFEST.md names scripts/figures/make_qualitative_figs.py) |
| W128 | docs/paper/bar/main.tex:200 (\includegraphics{qual_sr_bars.png}) | A_ctrl_rat bar label: 15/100 | as-run success count out of 100 for A_ctrl_rat | none (no generating script named in main.tex comments; MANIFEST.md names scripts/figures/make_qualitative_figs.py) |
| W129 | docs/paper/bar/main.tex:200 (\includegraphics{qual_sr_bars.png}) | D_gist bar label: 19/100 | as-run success count out of 100 for D_gist | none (no generating script named in main.tex comments; MANIFEST.md names scripts/figures/make_qualitative_figs.py) |
| W130 | docs/paper/bar/main.tex:200 (\includegraphics{qual_sr_bars.png}) | B_main bar label: 26/100 | as-run success count out of 100 for B_main | none (no generating script named in main.tex comments; MANIFEST.md names scripts/figures/make_qualitative_figs.py) |
| W131 | docs/paper/bar/main.tex:200 (\includegraphics{qual_sr_bars.png}) | C_retrieval bar label: 49/100 | as-run success count out of 100 for C_retrieval | none (no generating script named in main.tex comments; MANIFEST.md names scripts/figures/make_qualitative_figs.py) |
| W132 | docs/paper/bar/main.tex:200 (\includegraphics{qual_sr_bars.png}) | y-axis ticks: 0, 10, 20, 30, 40, 50, 60 | success rate y-axis scale tick marks | none (no generating script named in main.tex comments; MANIFEST.md names scripts/figures/make_qualitative_figs.py) |
| W133 | docs/paper/bar/main.tex:227 (\includegraphics{fig2_r1_dx.png}) | retrieval (green) moves the mean toward 0 with a wider per-episode spread | target displacement value (0) toward which retrieval pulls mean | none (no generating script named in main.tex comments; MANIFEST.md names scripts/figures/make_r1_figure.py) |
| W134 | docs/paper/bar/main.tex:227 (\includegraphics{fig2_r1_dx.png}) | Round-1 $\Delta$X (grid units), mean $\pm$ SD | index of round analyzed for lateral displacement | none (no generating script named in main.tex comments; MANIFEST.md names scripts/figures/make_r1_figure.py) |
| W135 | docs/paper/bar/main.tex:227 (\includegraphics{fig2_r1_dx.png}) | A_action_only data label: -16.6±8.6 | mean ± SD of round-1 ΔX in grid units for A_action_only | none (no generating script named in main.tex comments; MANIFEST.md names scripts/figures/make_r1_figure.py) |
| W136 | docs/paper/bar/main.tex:227 (\includegraphics{fig2_r1_dx.png}) | A_ctrl_rat data label: -15.8±10.1 | mean ± SD of round-1 ΔX in grid units for A_ctrl_rat | none (no generating script named in main.tex comments; MANIFEST.md names scripts/figures/make_r1_figure.py) |
| W137 | docs/paper/bar/main.tex:227 (\includegraphics{fig2_r1_dx.png}) | D_gist data label: -18.1±7.9 | mean ± SD of round-1 ΔX in grid units for D_gist | none (no generating script named in main.tex comments; MANIFEST.md names scripts/figures/make_r1_figure.py) |
| W138 | docs/paper/bar/main.tex:227 (\includegraphics{fig2_r1_dx.png}) | B_main data label: -16.7±8.5 | mean ± SD of round-1 ΔX in grid units for B_main | none (no generating script named in main.tex comments; MANIFEST.md names scripts/figures/make_r1_figure.py) |
| W139 | docs/paper/bar/main.tex:227 (\includegraphics{fig2_r1_dx.png}) | C_retrieval data label: -7.1±14.4 | mean ± SD of round-1 ΔX in grid units for C_retrieval | none (no generating script named in main.tex comments; MANIFEST.md names scripts/figures/make_r1_figure.py) |
| W140 | docs/paper/bar/main.tex:227 (\includegraphics{fig2_r1_dx.png}) | D6 memoryless teacher −23.5 (pre-registered reference, no σ) | pre-registered reference round-1 ΔX fingerprint for D6 memoryless teacher | none (no generating script named in main.tex comments; MANIFEST.md names scripts/figures/make_r1_figure.py) |
| W141 | docs/paper/bar/main.tex:227 (\includegraphics{fig2_r1_dx.png}) | memory-teacher last quartile −15.8 (pre-registered reference, no σ) | pre-registered reference round-1 ΔX fingerprint for memory teacher last quartile | none (no generating script named in main.tex comments; MANIFEST.md names scripts/figures/make_r1_figure.py) |
| W142 | docs/paper/bar/main.tex:227 (\includegraphics{fig2_r1_dx.png}) | y-axis ticks: -25, -20, -15, -10, -5, 0, 5 | round-1 ΔX y-axis scale tick marks (grid units) | none (no generating script named in main.tex comments; MANIFEST.md names scripts/figures/make_r1_figure.py) |
