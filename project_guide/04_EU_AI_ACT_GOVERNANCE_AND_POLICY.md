# Step 4: EU AI Act Governance & Policy Guide

This guide covers the **policy, ethics, and governance angle** of WorkforceGuard.

> **Scope note:** Our data is a U.S. survey and U.S. labour data. We map it onto EU law as a **comparative lens**, not because the Act applies to U.S. respondents. WorkforceGuard itself is a descriptive dashboard, not a high-risk AI system, so it reports **no conformity status of its own**.

---

## 1. What is the EU AI Act (Regulation (EU) 2024/1689)?

The European Union Artificial Intelligence Act is the world’s first comprehensive legal framework for artificial intelligence. It uses a **risk-based approach**:

```
[ Unacceptable Risk ] ──> Banned, Art. 5 (e.g., social scoring, emotion recognition at work)
[ High Risk ]         ──> Strictly Regulated, Annex III (e.g., Hiring, Promotion, Worker Monitoring)
[ Specific Risk ]     ──> Transparency, Art. 50 (e.g., Chatbots, Deepfakes, Emotion-recognition disclosure)
[ Minimal Risk ]      ──> Unregulated (e.g., Spam filters, AI video games)
```

### Timeline
* **2 Feb 2025**: Art. 5 prohibitions apply (including emotion recognition in the workplace).
* **Aug 2026**: Art. 50 transparency obligations apply.
* **2 Dec 2027**: Annex III high-risk obligations apply — deferred from 2 Aug 2026 by the 2026 Digital Omnibus.

---

## 2. Why Are Workplace & HR AI Systems Classified as "High-Risk"?

Under **Annex III, point 4** of the EU AI Act:
> *(a) "AI systems intended to be used for the recruitment or selection of natural persons, in particular to place targeted job advertisements, to analyse and filter job applications, and to evaluate candidates";*
> *(b) "AI systems intended to be used to make decisions affecting terms of work-related relationships, the promotion or termination of work-related contractual relationships, to allocate tasks based on individual behaviour or personal traits or characteristics or to monitor and evaluate the performance and behaviour of persons in such relationships."*

Monitoring and evaluating worker performance and behaviour is therefore **high-risk under Annex III, point 4(b)** — it is not an Art. 50 transparency case. Separately, **emotion recognition in the workplace** (the Commission's guidelines include recruitment) is **prohibited under Art. 5(1)(f)** since 2 Feb 2025, except for medical or safety reasons.

### Why the Law Cares:
A hiring or promotion decision directly determines an individual's livelihood, economic security, and civil rights. If an automated algorithm contains racial, gender, or age bias, it can systematically lock qualified candidates out of the economy at scale.

### Penalties (Art. 99):
* Prohibited practices: up to **€35M or 7%** of worldwide annual turnover (Art. 99(3)).
* Breaching high-risk obligations: up to **€15M or 3%** (Art. 99(4)).

---

## 3. How Our Survey Data Maps to the Law

Our lookup table `dim_ai_use_cases` maps each of the 5 Pew ATP Wave 119 items to its legal classification:

| Workplace AI Application | Pew Item | EU AI Act Classification | Legal Basis |
|---|---|---|---|
| **AI Reviewing Job Applications** | AIWRKH2_a | **High-Risk** | Annex III, point 4(a): screening and evaluating applicants |
| **AI Making Final Hiring Decisions** | AIWRKH2_b | **High-Risk** | Annex III, point 4(a): recruitment or selection |
| **AI Recording Workers' Computer Activity** | AIWRKM2_b | **High-Risk** | Annex III, point 4(b): monitoring performance and behaviour |
| **AI Deciding Promotions** | AIWRKM4_a | **High-Risk** | Annex III, point 4(b): decisions on promotion |
| **AI Analyzing Employees' Facial Expressions** | FACERECWK2_b | **Prohibited where it infers emotions** | Art. 5(1)(f): emotion recognition in the workplace |

Among all U.S. adults, net opposition (oppose − favor) ranges from +13.6 pp (reviewing applications) to +63.8 pp (final hiring decisions); facial-expression analysis is +61.6 pp.

---

## 4. Obligations to Evidence (High-Risk Employment AI)

The dashboard's **"Obligations to evidence"** panel lists what a provider or deployer of an Annex III, point 4 system would have to evidence, each with an owner badge (PROVIDER / DEPLOYER). It is a checklist of obligations, not a score: the old hardcoded conformity badges and the `eu_ai_act.py` conformity engine are retired to `archive/legacy_v1/`.

For Annex III, point 4 systems the conformity assessment follows the **internal-control route** (Art. 43(2), Annex VI) — **no notified body** — followed by CE marking (Art. 48).

### 1. Risk Management System (Article 9) — Provider
* Continuous, documented identification and mitigation of risks across the lifecycle.

### 2. Data Governance & Bias Testing (Article 10) — Provider
* Training, validation and test datasets must be examined for possible biases.
* Statistical disparity testing across demographic cohorts (e.g., EEOC 4/5ths Rule) is good practice.

### 3. Technical Documentation & Record-Keeping (Articles 11, 12, 19, 26(6)) — Provider / Deployer
* Annex IV technical documentation, system architecture and limitations (Art. 11).
* Automatic event logging over the system's lifetime (Art. 12); logs kept for at least 6 months (Art. 19 for providers, Art. 26(6) for deployers). "Tamper-evident" storage is good practice, not a statutory term.

### 4. Transparency & Human Oversight (Articles 13-14) — Provider
* Instructions for use (Art. 13).
* The system must be designed so that people can effectively monitor it, override its output and stop it (Art. 14).
* Mandatory human sign-off on adverse decisions is a good control, not a statutory rule.

### 5. Accuracy, Robustness & Cybersecurity (Article 15) — Provider
* Declared accuracy levels; resilience against errors and adversarial attacks.

### Also on the panel
* **Quality management system (Art. 17)** — Provider: documented policies, procedures and post-market monitoring.
* **Deployer duties (Art. 26)** — Deployer: use per instructions, trained human overseers, keep logs ≥ 6 months, and **inform workers and their representatives before use (Art. 26(7))**.
* **Right to explanation (Art. 86)** — Deployer: affected persons may request an explanation of decisions based on the system's output.
