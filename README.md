# Ensemble of Specialized LLMs (ES-LLMs)

**Official Reproducibility Repository for the AIED 2026 Paper:**
*"From Untamed Black Box to Interpretable Pedagogical Orchestration: The Ensemble of Specialized LLMs Architecture for Adaptive Tutoring"*

## 🎯 Purpose of this Repository
This repository is designed to provide methodological transparency for learning sciences researchers and reviewers. 

To guarantee procedural fairness and pedagogical safety, our ES-LLMs architecture strictly decouples pedagogical decision-making from standard large language model text generation. Instead of relying on stochastic prompt engineering, the tutor's behavior is driven by deterministic, interpretable rules and cognitive models (such as Bayesian Knowledge Tracing). This repository exposes that exact underlying logic.

## 🗂️ What's Included?

### 1. The Core Pedagogical Logic (`/agents` & `/policy`)
These Python files demonstrate the "brain" of the tutor—the condition-action rules and priority hierarchies that dictate *when* and *how* the system intervenes.
* **`agents/orchestrator.py`**: The Meta-Orchestrator that evaluates learner state and arbitrates our strict priority hierarchy (`Ethics > Assessment > Feedback > Scaffolding > Motivation`).
* **`agents/assessment_bot.py`**: The mathematical implementation of our Bayesian Knowledge Tracing (BKT) mechanics used to dynamically track learner mastery ($pL$).
* **`agents/scaffold_bot.py`**: The logic that computes exact scaffolding depth strictly based on consecutive student errors to prevent over-helping and maintain the Zone of Proximal Development.
* **`agents/ethics_bot.py`**: The safety constraint definitions (e.g., enforcing the "attempt-before-hint" rule to prevent system gaming).
* **`policy/pedagogical_policy.py`**: The explicit condition-action mappings defining the active pedagogical policy sequence.

### 2. Human Evaluation Transparency (`/evaluation`)
* **`HUMAN_EVALUATION_RUBRICS.md`**: The comprehensive 7-dimension evaluation rubric (Likert 1-5 scale) utilized by our expert panel of educators to benchmark the system's pedagogical performance.

### 3. Data Collection Transparency (`/examples`)
* **`Consolidated_Master_Output.csv`**: An anonymized raw data export containing the 5-point Likert scores and justifications from our expert human panel evaluation across the 24 paired mathematical scenarios.
* **`sim_N2400_final_v2.csv`**: An unedited raw sample dataset exported directly from our high-throughput automated Monte Carlo simulations (N=2,400 runs), demonstrating our specific constraint adherence and mastery gain logging pipeline constraint by constraint.

---
*(Note: For confidentiality and security, proprietary database schema, explicit system prompt templates, comprehensive domain expert knowledge bases, and API endpoints have been intentionally omitted. This repository serves specifically to satisfy methodological transparency regarding the symbolic rule arbitration and evaluation rubrics).*

## 👥 Authors & Citation

* **Nizam Kadir** [[ORCID: 0000-0002-6725-1133]](https://orcid.org/0000-0002-6725-1133) (Corresponding Author: `nizam_kadir@mymail.sutd.edu.sg`)
* **Nachamma Sockalingam** [[ORCID: 0000-0002-9477-428X]](https://orcid.org/0000-0002-9477-428X)
* **Dorien Herremans** [[ORCID: 0000-0001-8607-1640]](https://orcid.org/0000-0001-8607-1640)

*Singapore University of Technology and Design, Singapore 487372, Singapore*

If you build upon this architecture or utilize the pedagogical ruleset in your research, please cite our AIED 2026 paper:

```bibtex
@inproceedings{esllms2026,
  title={From Untamed Black Box to Interpretable Pedagogical Orchestration: The Ensemble of Specialized LLMs Architecture for Adaptive Tutoring},
  author={Kadir, Nizam and Sockalingam, Nachamma and Herremans, Dorien},
  booktitle={Proceedings of the 27th International Conference on Artificial Intelligence in Education (AIED 2026)},
  year={2026},
  publisher={Springer}
}
```
