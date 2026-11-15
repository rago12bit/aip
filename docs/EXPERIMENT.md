# Experiment: MedRule against simpler methods

Vignettes are hand-written by the project author after the knowledge base was built, so this
shows internal consistency on noisy and overlapping presentations, **not clinical accuracy**.
Methods: `full` = the whole system; `no_negative` = negative rules removed; `crisp_fever` =
hard 100.4 F / 102 F thresholds instead of fuzzy degrees; `overlap` = share of a disease's
symptoms reported (baseline).

## General set (40 cases)

A fair sample of typical and noisy presentations.

| Method | Top-1 correct | Top-3 contains answer |
|---|---|---|
| full | 38/40 (95%) | 40/40 (100%) |
| no_negative | 38/40 (95%) | 40/40 (100%) |
| crisp_fever | 38/40 (95%) | 40/40 (100%) |
| overlap | 38/40 (95%) | 40/40 (100%) |

Cases where the full system's top answer was not acceptable:

- high_fever, headache, joint_pain, body_aches, nausea at 103.5 F: expected ['dengue'], got ['influenza', 'dengue']
- high_fever, cough, chest_pain, body_aches, fatigue at 103.4 F: expected ['pneumonia'], got ['influenza', 'pneumonia', 'covid19']

## Targeted set (10 cases)

Written to probe negative evidence and graded fever. Not a fair sample: it shows what each feature is for.

| Method | Top-1 correct | Top-3 contains answer |
|---|---|---|
| full | 10/10 (100%) | 10/10 (100%) |
| no_negative | 9/10 (90%) | 10/10 (100%) |
| crisp_fever | 9/10 (90%) | 10/10 (100%) |
| overlap | 8/10 (80%) | 10/10 (100%) |
