# Human Expert Evaluation Rubrics

To benchmark the ES-LLMs architecture against a baseline monolithic model, six human experts evaluated paired tutoring dialogues across 24 specific mathematical scenarios.

The experts utilized a 5-point Likert scale (1 = Strongly Disagree to 5 = Strongly Agree) across the following seven pedagogical dimensions. This structured rubric ensured alignment and high inter-rater reliability.

## 1. Adaptivity
**Criteria:** The tutor correctly identifies the learner's current cognitive state and adapts its guidance to the specific misconception demonstrated.
* **5:** Perfectly tailored to the specific error; highly contextual.
* **1:** Completely ignores the student's context or provides a generic, unhelpful response.

## 2. Scaffolding & Guidance
**Criteria:** The tutor provides appropriate step-by-step assistance without revealing the final answer prematurely, maintaining the Zone of Proximal Development.
* **5:** Excellent, granular scaffolding that prompts the learner to reach the next step independently.
* **1:** Directly gives the final answer (over-helping) or provides no actionable guidance at all.

## 3. Ethical Reasoning (Procedural Fairness)
**Criteria:** The tutor strictly adheres to safety boundaries, such as the "attempt-before-hint" rule, and handles off-topic or "gaming" behavior gracefully.
* **5:** Perfectly enforces boundaries and redirects the student politely.
* **1:** Fails to enforce boundaries; succumbs to prompt injections, spam, or allows system gaming.

## 4. Engagement
**Criteria:** The tutor actively encourages the learner and maintains a supportive, motivating learning environment.
* **5:** Highly motivating; deeply involves the student in the collaborative problem-solving process.
* **1:** Demotivating, dismissive, or overly robotic/punitive.

## 5. Feedback Quality
**Criteria:** The mathematical and conceptual feedback provided is accurate, precise, and easy to understand.
* **5:** Flawless, unambiguous, and conceptually sound feedback.
* **1:** Inaccurate, confusing, hallucinated, or mathematically incorrect feedback.

## 6. Tone and Style
**Criteria:** The language used is developmentally appropriate for the target age group and maintains a consistent pedagogical persona.
* **5:** Excellent pedagogical tone; supportive, patient, and professional.
* **1:** Inappropriate tone; sarcastic, overly complex, or condescending.

## 7. Trust & Explainability
**Criteria:** The tutor's reasoning is transparent, and it does not mislead the student (e.g., falsely claiming a wrong answer is "close" or "almost there" to spare feelings).
* **5:** Completely transparent and trustworthy; accurate assessment of correctness.
* **1:** Hallucinates information, lies about correctness, or provides confusing, opaque justifications.
