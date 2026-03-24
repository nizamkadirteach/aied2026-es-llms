# Ensemble of Specialized LLMs (ES-LLMs) - Pedagogical Logic

This repository contains the core pedagogical logic and arbitration rules for the **ES-LLMs** architecture, developed for the AIED 2026 paper:
*"From Untamed Black Box to Interpretable Pedagogical Orchestration: The Ensemble of Specialized LLMs Architecture for Adaptive Tutoring"*

## Overview

To guarantee procedural fairness and pedagogical safety, ES-LLMs strictly decouple pedagogical decision-making from natural language generation. The files in this repository demonstrate the deterministic rules, Knowledge Tracing models, and priority hierarchies that govern the system's core orchestration.

## Contents

* **`agents/orchestrator.py`**: The Meta-Orchestrator that evaluates learner state and arbitrates the strict priority hierarchy (`Ethics > Assessment > Feedback > Scaffolding > Motivation`).
* **`policy/pedagogical_policy.py`**: The specific condition-action rule mappings defining the active pedagogical policy sequence.
* **`agents/ethics_bot.py`**: Computes and enforces non-negotiable safety rules (e.g., attempt-before-hint, maximum hint caps) to prevent system gaming.
* **`agents/scaffold_bot.py`**: Calculates scaffolding depth strictly based on consecutive errors to prevent over-helping and maintain the zone of proximal development.
* **`agents/assessment_bot.py`**: Implements the Bayesian Knowledge Tracing (BKT) mechanics to actively update learner mastery ($pL$) upon answer attempts.
* **`evaluation/`**: Contains the comprehensive 7-dimension Human Evaluation Rubrics (Likert 1-5) utilized by our expert panel to benchmark the system's pedagogical performance.
* **`examples/`**: Contains an unedited raw sample dataset (`Consolidated_Master_Output.csv`) exported directly from our automated simulations to demonstrate data collection transparency.

---
*(Note: For confidentiality and security, proprietary database models, explicit prompt templates, domain expert knowledge bases, complete affective inference models, and API endpoints have been omitted. This repository serves specifically to satisfy methodological transparency regarding the symbolic rule arbitration.)*
