#  LegalDrishti AI - Golden Evaluation Dataset & Benchmark Suite

##  Dataset Overview

This golden evaluation dataset contains **75 curated Indian statutory & precedent query scenarios** specifically developed to benchmark the accuracy, hallucination resistance, and citation precision of the **LegalDrishti AI** Dual-Stream RAG pipeline.

Each scenario has been curated with:
* **`question`**: Realistic advocate/client inquiry.
* **`category` & `sub_category`**: Domain classification.
* **`statute` & `relevant_sections`**: Ground-truth legislative provisions.
* **`ground_truth_context`**: Verbatim statutory text and ratios that *must* be retrieved.
* **`ground_truth_answer`**: Verified, legally accurate answer written according to Indian jurisprudence.
* **`key_statutory_ingredients`**: Essential legal elements for compliance verification.
* **`citation_benchmark`**: Authoritative Supreme Court of India precedents.
* **`complexity`**: Basic, Intermediate, or Advanced.

---

##  Distribution of the 75 Scenarios

| Pillar | Statutory Domain | Scenarios | Key Highlights |
| :---: | :--- | :---: | :--- |
| **1** | **Negotiable Instruments Act, 1881** | 10 | Limitation under Sec 138/142, Interim compensation Sec 143A, Vicarious liability Sec 141, Deemed notice, Compounding. |
| **2** | **Criminal Procedure & Bail (BNSS 2023)** | 12 | Anticipatory bail Sec 482, Default bail Sec 187, Remand flexibility, Mandatory videography Sec 105, Zero FIR Sec 173, In absentia trial Sec 356. |
| **3** | **Substantive Criminal Law (BNS 2023)** | 10 | Murder Sec 103, Snatching Sec 304, Organized crime Sec 111, Terrorist acts Sec 113, Hit-and-run Sec 106(2), Deceitful intercourse Sec 69, Mob lynching Sec 103(2). |
| **4** | **Law of Evidence (BSA 2023)** | 8 | Electronic certificate Sec 63 (ex-65B), Primary digital evidence Sec 57, Police confession ban Sec 23(1), Discovery Sec 23(2), Dying declarations Sec 26(a). |
| **5** | **Constitutional Law & Writs** | 8 | Habeas Corpus, Right to Privacy (Puttaswamy), Manifest arbitrariness Art 14, Self-incrimination Art 20(3), Internet rights Art 19(1)(a), Mandamus. |
| **6** | **Civil Procedure & Specific Relief (CPC / SRA)** | 8 | Rejection of plaint Order 7 Rule 11, Injunctions Order 39, Res Judicata Sec 11, Second Appeal Sec 100, Mandatory specific performance Sec 10 SRA. |
| **7** | **Commercial, Arbitration & Insolvency (IBC)** | 8 | Sec 9 vs Sec 17 interim relief, Patent illegality Sec 34, Sec 7 CIRP default, Sec 9 pre-existing dispute, Sec 14 Moratorium, Liquidated damages Sec 74. |
| **8** | **Consumer Protection & Cyber Law (CPA / IT / DPDP)** | 5 | Pecuniary jurisdiction, Product liability, Intermediary safe harbor Sec 79 IT Act, Identity theft Sec 66C, Data Principal rights DPDP 2023. |
| **9** | **Property Law & Real Estate (TPA 1882 / RERA)** | 4 | Lis Pendens Sec 52, Gift deed execution Sec 123, Fraudulent transfer Sec 53, RERA Sec 18 delayed possession refunds. |
| **10** | **Family & Matrimonial Law (HMA / PWDVA)** | 2 | Waiving 6-month cooling period Sec 13B(2) HMA (Amardeep Singh), Shared household rights in in-laws' home (Satish Chander Ahuja). |
| **TOTAL** | | **75** | **Comprehensive legal coverage** |

---

##  File Formats Available

1. **`golden_dataset.json`**: Structured JSON array suitable for automated evaluation scripts, Ragas `Dataset` loading, or API payload execution.
2. **`golden_dataset.csv`**: Tabular format for spreadsheet review, pandas dataframes, or quick inspection.
3. **`generate_dataset.py`**: Python script used to regenerate or expand the dataset.
4. **`evaluate_pipeline.py`**: Evaluation runner script that tests the live pipeline against this dataset.

---

##  How to Run the Evaluation Benchmark

Run the evaluation runner directly using Python:

```bash
python evaluation/evaluate_pipeline.py --samples 10
```

To run across all 75 scenarios:

```bash
python evaluation/evaluate_pipeline.py --all
```
