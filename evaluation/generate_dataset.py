"""
Generator script to produce the 75-scenario Indian Legal Golden Dataset for LegalDrishti AI.
"""

import json
import csv
from pathlib import Path

DATASET_ITEMS = [
    # ---------------------------------------------------------
    # PILLAR 1: Negotiable Instruments Act (Cheque Dishonour)
    # ---------------------------------------------------------
    {
        "id": "NI-001",
        "category": "Negotiable Instruments Act",
        "sub_category": "Cheque Dishonour Limitation",
        "statute": "Negotiable Instruments Act, 1881",
        "relevant_sections": ["Section 138", "Section 142(1)(b)"],
        "question": "What is the statutory limitation period to send a legal notice and file a criminal complaint after a bank return memo for cheque bounce?",
        "ground_truth_context": "Under Section 138 proviso (b) of the Negotiable Instruments Act 1881, the payee or holder in due course must make a demand for payment by giving a notice in writing within thirty (30) days of the receipt of information from the bank regarding the return of the cheque as unpaid. If the drawer fails to make payment within fifteen (15) days of the receipt of notice, under Section 142(1)(b), the complaint must be made within one (1) month of the date on which the cause-of-action arises.",
        "ground_truth_answer": "1. Demand Notice: Must be dispatched within 30 days of receiving the cheque return memo from the bank.\n2. Cure Period: The drawer is granted 15 days from the date of receipt of notice to make payment.\n3. Filing Limitation: If payment is not made, cause of action arises on the 16th day, and the complaint under Section 138/142(1)(b) must be filed before the Magistrate within 1 month from that date.",
        "key_statutory_ingredients": ["30 days notice", "15 days cure period", "1 month limitation under Sec 142(1)(b)"],
        "citation_benchmark": "MSR Leathers v. S. Palaniappan (2013) 1 SCC 177",
        "complexity": "Intermediate"
    },
    {
        "id": "NI-002",
        "category": "Negotiable Instruments Act",
        "sub_category": "Territorial Jurisdiction",
        "statute": "Negotiable Instruments Act, 1881",
        "relevant_sections": ["Section 142(2)"],
        "question": "Where must a Section 138 cheque bounce complaint be filed if the cheque was delivered for collection through an account?",
        "ground_truth_context": "Following the 2015 amendment, Section 142(2)(a) mandates that the offence under Section 138 shall be inquired into and tried only by a court within whose local jurisdiction the branch of the bank where the payee or holder in due course maintains the account is situated.",
        "ground_truth_answer": "Under Section 142(2)(a) of the Negotiable Instruments Act (amended in 2015), the complaint must be filed exclusively in the court having territorial jurisdiction over the specific bank branch where the payee maintains their account and deposited the cheque for collection.",
        "key_statutory_ingredients": ["Payee bank branch location", "Account maintained branch", "Section 142(2)(a)"],
        "citation_benchmark": "Bridgestone India Pvt. Ltd. v. Inderpal Singh (2016) 2 SCC 341",
        "complexity": "Basic"
    },
    {
        "id": "NI-003",
        "category": "Negotiable Instruments Act",
        "sub_category": "Interim Compensation",
        "statute": "Negotiable Instruments Act, 1881",
        "relevant_sections": ["Section 143A"],
        "question": "Can the trial court order the accused drawer to pay interim compensation in a Section 138 trial, and what is the legal cap?",
        "ground_truth_context": "Section 143A empowers the Court trying an offence under Section 138 to direct the drawer to pay interim compensation to the complainant. The interim compensation shall not exceed twenty per cent (20%) of the amount of the cheque, payable within 60 days (extendable by 30 days).",
        "ground_truth_answer": "Yes, under Section 143A of the NI Act, the trial court has discretionary power to order interim compensation up to a statutory maximum of 20% of the cheque amount. The amount must be deposited within 60 days of the order, extendable by an additional 30 days upon showing sufficient cause.",
        "key_statutory_ingredients": ["Maximum 20% of cheque amount", "60 days + 30 days extension", "Section 143A discretionary power"],
        "citation_benchmark": "Rakesh Ranjan Shrivastava v. State of Jharkhand (2024) INSC 224",
        "complexity": "Intermediate"
    },
    {
        "id": "NI-004",
        "category": "Negotiable Instruments Act",
        "sub_category": "Corporate Vicarious Liability",
        "statute": "Negotiable Instruments Act, 1881",
        "relevant_sections": ["Section 141"],
        "question": "What averments are mandatory in a Section 138 complaint to hold a company director vicariously liable under Section 141?",
        "ground_truth_context": "Under Section 141 of the NI Act, every person who at the time the offence was committed was in charge of, and was responsible to the company for the conduct of the business of the company, is deemed guilty. Specific averment detailing how the director was in day-to-day management and responsible for business conduct is mandatory; mere designation as director is insufficient.",
        "ground_truth_answer": "To hold a director vicariously liable under Section 141: (1) The company must be arraigned as a primary accused; (2) The complaint must contain clear, specific factual averments demonstrating that the director was in charge of and responsible to the company for the conduct of its business at the exact time of the offence.",
        "key_statutory_ingredients": ["Company must be arrayed as accused", "Specific averment of day-to-day management", "Aneeta Hada principle"],
        "citation_benchmark": "Aneeta Hada v. Godfather Travels & Tours (P) Ltd. (2012) 5 SCC 661",
        "complexity": "Advanced"
    },
    {
        "id": "NI-005",
        "category": "Negotiable Instruments Act",
        "sub_category": "Stop Payment Instructions",
        "statute": "Negotiable Instruments Act, 1881",
        "relevant_sections": ["Section 138"],
        "question": "Does a cheque dishonoured due to 'Stop Payment instructions by drawer' attract liability under Section 138?",
        "ground_truth_context": "The Supreme Court settled that Section 138 is attracted even when the cheque is returned unpaid with the endorsement 'stop payment', provided the statutory notice requirement is complied with and the debt is legally enforceable.",
        "ground_truth_answer": "Yes. A return memo showing 'Stop Payment' falls squarely within the ambit of Section 138 of the NI Act. If the drawer fails to make payment within 15 days of receiving the statutory demand notice, criminal liability is invoked, subject to rebutting the presumption under Section 139.",
        "key_statutory_ingredients": ["Stop payment equates to dishonour", "Section 138 applies", "Modi Cements doctrine"],
        "citation_benchmark": "Modi Cements Ltd. v. Kuchil Kumar Nandi (1998) 3 SCC 249",
        "complexity": "Basic"
    },
    {
        "id": "NI-006",
        "category": "Negotiable Instruments Act",
        "sub_category": "Security Cheque & Presumption",
        "statute": "Negotiable Instruments Act, 1881",
        "relevant_sections": ["Section 138", "Section 139"],
        "question": "Can a cheque handed over as 'security' be prosecuted under Section 138 if the debt matures subsequently?",
        "ground_truth_context": "Under Section 139, there is a legal presumption that the cheque was received for discharge of a debt. If on the date of presentation the liability exists and exceeds or equals the cheque amount, a security cheque is enforceable under Section 138.",
        "ground_truth_answer": "Yes. If an outstanding legally enforceable debt or liability exists on the date of presentation or maturity, the drawer cannot escape Section 138 liability merely by labeling the instrument a 'security cheque'. The burden lies upon the accused to rebut the presumption under Section 139 by preponderance of probabilities.",
        "key_statutory_ingredients": ["Presumption under Sec 139", "Matured liability on date of presentation", "Preponderance of probabilities"],
        "citation_benchmark": "Sripati Singh v. State of Jharkhand 2021 SCC OnLine SC 1002",
        "complexity": "Intermediate"
    },
    {
        "id": "NI-007",
        "category": "Negotiable Instruments Act",
        "sub_category": "Deemed Service of Notice",
        "statute": "Negotiable Instruments Act, 1881 / General Clauses Act, 1897",
        "relevant_sections": ["Section 138 proviso (b)", "Section 27 General Clauses Act"],
        "question": "What is the legal effect when a Section 138 statutory demand notice sent by registered post is returned as 'unclaimed' or 'refused'?",
        "ground_truth_context": "Under Section 27 of the General Clauses Act 1897 read with Section 114 of the Evidence Act / Section 119 BSA, where a notice is sent by registered post prepaid to the correct address, service is deemed to be effected unless contrary is proved. Refusal or deliberate non-claim constitutes valid deemed service.",
        "ground_truth_answer": "When statutory notice is sent by registered post with correct address and prepaid postage, endorsements like 'unclaimed', 'refused', or 'addressee not found' constitute valid deemed service under Section 27 of the General Clauses Act. The 15-day cure period begins from the date of return endorsement.",
        "key_statutory_ingredients": ["Deemed service under Sec 27 General Clauses Act", "Correct postal address", "CC Alavi Haji 3-judge bench ruling"],
        "citation_benchmark": "C.C. Alavi Haji v. Palapetty Muhammed (2007) 6 SCC 555",
        "complexity": "Intermediate"
    },
    {
        "id": "NI-008",
        "category": "Negotiable Instruments Act",
        "sub_category": "Compounding of Offence",
        "statute": "Negotiable Instruments Act, 1881",
        "relevant_sections": ["Section 147"],
        "question": "Can an offence under Section 138 be compounded after conviction at the appellate or revisional stage, and are there grading costs?",
        "ground_truth_context": "Section 147 of the NI Act states that every offence punishable under this Act shall be compoundable. Damodar S. Prabhu laid down graded compounding costs: 10% before Sessions Court, 15% before High Court, 20% before Supreme Court.",
        "ground_truth_answer": "Yes, Section 147 expressly makes cheque bounce offences compoundable at any stage, including appellate or revisional stages. However, following the Supreme Court's guidelines in Damodar S. Prabhu, compounding at late stages attracts graded costs payable to DLSA (10% at Sessions, 15% at High Court, 20% at Supreme Court), subject to judicial discretion.",
        "key_statutory_ingredients": ["Section 147 non-obstante compounding", "Graded cost scale", "Damodar S. Prabhu guidelines"],
        "citation_benchmark": "Damodar S. Prabhu v. Sayed Babalal H. (2010) 5 SCC 663",
        "complexity": "Intermediate"
    },
    {
        "id": "NI-009",
        "category": "Negotiable Instruments Act",
        "sub_category": "Appellate Deposit",
        "statute": "Negotiable Instruments Act, 1881",
        "relevant_sections": ["Section 148"],
        "question": "Is the appellate court empowered to order a minimum deposit against the conviction order under Section 148, and is it retrospective?",
        "ground_truth_context": "Section 148 empowers the Appellate Court to direct the appellant to deposit a minimum of twenty percent (20%) of the fine or compensation awarded by the trial court. Surinder Singh Deswal affirmed that Section 148 applies retrospectively to pending complaints.",
        "ground_truth_answer": "Under Section 148 of the NI Act, the Appellate Court hearing an appeal against conviction may direct the appellant to deposit a minimum of 20% of the fine or compensation. The provision applies retrospectively to complaints filed prior to the 2018 amendment.",
        "key_statutory_ingredients": ["Minimum 20% deposit", "Appellate stage order", "Retrospective applicability"],
        "citation_benchmark": "Surinder Singh Deswal v. Virender Gandhi (2019) 11 SCC 341",
        "complexity": "Intermediate"
    },
    {
        "id": "NI-010",
        "category": "Negotiable Instruments Act",
        "sub_category": "Partnership Firm Liability",
        "statute": "Negotiable Instruments Act, 1881",
        "relevant_sections": ["Section 141(1)", "Section 141(2)"],
        "question": "Can a sleeping partner of a firm be held liable under Section 138 if the cheque was signed by the managing partner?",
        "ground_truth_context": "Section 141 explanation (a) states that 'company' includes a firm or association of individuals. A partner who was not in charge of or responsible for the firm's business at the time of the transaction cannot be held liable merely because of being a partner.",
        "ground_truth_answer": "No, a sleeping partner cannot be prosecuted vicariously under Section 141 unless the complainant specifically pleads and proves that such partner had an active role in the transaction and was in charge of the conduct of the firm's business when the dishonour occurred.",
        "key_statutory_ingredients": ["Firm included in company definition", "Active role required", "Sleeping partner protected"],
        "citation_benchmark": "K.P.G. Nair v. Jindal Menthol India Ltd. (2001) 10 SCC 218",
        "complexity": "Advanced"
    },

    # ---------------------------------------------------------
    # PILLAR 2: Criminal Procedure & Bail under BNSS, 2023
    # ---------------------------------------------------------
    {
        "id": "BNSS-001",
        "category": "Criminal Procedure & Bail",
        "sub_category": "Anticipatory Bail",
        "statute": "Bharatiya Nagarik Suraksha Sanhita, 2023",
        "relevant_sections": ["Section 482 BNSS"],
        "question": "What are the governing statutory conditions and forum for seeking Anticipatory Bail under Section 482 of the BNSS 2023?",
        "ground_truth_context": "Section 482 BNSS (replacing Section 438 CrPC) provides that when any person has reason to believe that he may be arrested on an accusation of having committed a non-bailable offence, he may apply to the High Court or the Court of Session for a direction that in the event of such arrest, he shall be released on bail.",
        "ground_truth_answer": "Under Section 482 of BNSS 2023: (1) An application for anticipatory bail lies concurrently before the High Court or the Court of Session; (2) The applicant must demonstrate a reasonable apprehension of arrest for a non-bailable offence; (3) The court evaluates nature and gravity of accusation, criminal antecedents, flight risk, and likelihood of tampering with evidence; (4) The court may impose conditions like cooperating with investigation and not leaving India without permission.",
        "key_statutory_ingredients": ["Section 482 BNSS", "High Court or Sessions Court", "Apprehension of arrest in non-bailable offence", "No automatic blanket protection"],
        "citation_benchmark": "Sushila Aggarwal v. State (NCT of Delhi) (2020) 5 SCC 1",
        "complexity": "Advanced"
    },
    {
        "id": "BNSS-002",
        "category": "Criminal Procedure & Bail",
        "sub_category": "Default Bail",
        "statute": "Bharatiya Nagarik Suraksha Sanhita, 2023",
        "relevant_sections": ["Section 187(2) BNSS", "Section 187(3) BNSS"],
        "question": "What is the statutory custody period for claiming Default Bail (Statutory Bail) under Section 187 of BNSS 2023?",
        "ground_truth_context": "Section 187(3) BNSS provides default bail upon failure to complete investigation within: (a) 90 days where investigation relates to an offence punishable with death, imprisonment for life or imprisonment for a term of not less than ten years; and (b) 60 days where the investigation relates to any other offence.",
        "ground_truth_answer": "Under Section 187(3) BNSS 2023, default bail is an indefeasible fundamental right if the police fail to file the chargesheet within: (1) 90 days for offences punishable with death, life imprisonment, or rigorous imprisonment of not less than 10 years; (2) 60 days for all other offences. The accused must be prepared to furnish bail bonds.",
        "key_statutory_ingredients": ["90 days for 10+ years/life/death", "60 days for other offences", "Indefeasible right under Art 21"],
        "citation_benchmark": "Bikramjit Singh v. State of Punjab (2020) 10 SCC 616",
        "complexity": "Intermediate"
    },
    {
        "id": "BNSS-003",
        "category": "Criminal Procedure & Bail",
        "sub_category": "Police Remand Flexibility",
        "statute": "Bharatiya Nagarik Suraksha Sanhita, 2023",
        "relevant_sections": ["Section 187(2) BNSS"],
        "question": "How does Section 187(2) of BNSS 2023 alter police custody remand compared to old Section 167(2) CrPC?",
        "ground_truth_context": "Under Section 187(2) BNSS, the Magistrate may authorize detention of the accused in police custody for a term not exceeding fifteen (15) days in the whole, or in parts, at any time during the initial forty (40) or sixty (60) days out of the total detention period of sixty or ninety days.",
        "ground_truth_answer": "Unlike the CrPC where the 15-day police remand was strictly limited to the first 15 days of arrest (CBI v. Anupam J. Kulkarni), Section 187(2) BNSS permits the 15 days of police custody to be taken in whole or in tranches across the initial 40 or 60 days of the total investigation period.",
        "key_statutory_ingredients": ["15 days police remand in parts", "Spread over first 40 or 60 days", "Overrules Anupam Kulkarni constraint"],
        "citation_benchmark": "V. Senthil Balaji v. State 2023 SCC OnLine SC 934",
        "complexity": "Advanced"
    },
    {
        "id": "BNSS-004",
        "category": "Criminal Procedure & Bail",
        "sub_category": "Mandatory Search Videography",
        "statute": "Bharatiya Nagarik Suraksha Sanhita, 2023",
        "relevant_sections": ["Section 105 BNSS"],
        "question": "What is the mandatory forensic requirement introduced by Section 105 of BNSS 2023 during search and seizure?",
        "ground_truth_context": "Section 105 of the BNSS mandates that the process of conducting search of a place or taking possession of any property, including preparation of the seizure list and signature of witnesses, shall be recorded through audio-video electronic means, preferably by mobile phone, and submitted to the Magistrate without delay.",
        "ground_truth_answer": "Section 105 BNSS makes audio-video electronic recording (videography) strictly mandatory for any search of premises and seizure of articles, including the recording of the seizure list (panchnama) and witness signatures, which must be transmitted to the Magistrate within 48 hours.",
        "key_statutory_ingredients": ["Mandatory audio-video electronic recording", "Seizure list videography", "Section 105 BNSS mandate"],
        "citation_benchmark": "Statutory Mandate under Section 105 BNSS (w.e.f. July 1, 2024)",
        "complexity": "Intermediate"
    },
    {
        "id": "BNSS-005",
        "category": "Criminal Procedure & Bail",
        "sub_category": "Zero FIR and Electronic FIR",
        "statute": "Bharatiya Nagarik Suraksha Sanhita, 2023",
        "relevant_sections": ["Section 173 BNSS"],
        "question": "What are the rules for filing a Zero FIR and electronic information (e-FIR) under Section 173 of BNSS 2023?",
        "ground_truth_context": "Section 173(1) BNSS codifies Zero FIR, mandating that information relating to a cognizable offence must be recorded irrespective of the area where the offence was committed. If given electronically, it must be taken on record and signed within three days by the informant.",
        "ground_truth_answer": "Under Section 173 BNSS: (1) Zero FIR: Any police station must register information of a cognizable offence regardless of jurisdiction and transfer it to the jurisdictional station; (2) E-FIR / Electronic Info: Can be submitted online, but the informant must physically sign it within 3 days for it to formally convert into an FIR.",
        "key_statutory_ingredients": ["Section 173 BNSS", "Mandatory registration irrespective of territorial jurisdiction", "3-day physical signature rule for e-FIR"],
        "citation_benchmark": "Lalita Kumari v. Govt. of U.P. (2014) 2 SCC 1",
        "complexity": "Basic"
    },
    {
        "id": "BNSS-006",
        "category": "Criminal Procedure & Bail",
        "sub_category": "Arrest Safeguards for Offences Under 7 Years",
        "statute": "Bharatiya Nagarik Suraksha Sanhita, 2023",
        "relevant_sections": ["Section 35(3) BNSS"],
        "question": "When can police make an arrest without a warrant for offences punishable with up to 7 years imprisonment under Section 35 BNSS?",
        "ground_truth_context": "Section 35(3) BNSS provides that for offences punishable with imprisonment for a term which may be less than seven years or may extend up to seven years, a notice of appearance shall be issued. Arrest shall not be made unless specific reasons recorded in writing show flight risk, tampering, or prevention of further offence.",
        "ground_truth_answer": "For offences punishable up to 7 years, arrest is not the rule. The police must issue a Notice of Appearance under Section 35(3) BNSS. Arrest is only permissible if specific conditions under Section 35(1)(b) exist (e.g. risk of absconding or tampering) and the officer records written justification; otherwise, non-compliance violates Arnesh Kumar guidelines.",
        "key_statutory_ingredients": ["Notice of appearance under Sec 35(3)", "Offences up to 7 years", "Written reasons mandatory"],
        "citation_benchmark": "Arnesh Kumar v. State of Bihar (2014) 8 SCC 273",
        "complexity": "Intermediate"
    },
    {
        "id": "BNSS-007",
        "category": "Criminal Procedure & Bail",
        "sub_category": "Handcuffing Provisions",
        "statute": "Bharatiya Nagarik Suraksha Sanhita, 2023",
        "relevant_sections": ["Section 43(3) BNSS"],
        "question": "What are the statutory parameters governing the use of handcuffs under Section 43(3) of BNSS 2023?",
        "ground_truth_context": "Section 43(3) BNSS allows a police officer to use handcuffs having regard to the nature and gravity of the offence, specifically for habitual, repeat offenders or persons involved in serious offences like organized crime, terrorism, drug trafficking, rape, acid attack, or murder.",
        "ground_truth_answer": "Under Section 43(3) BNSS, handcuffs are permissible only during arrest or production before court for specified heinous or organized crimes (terrorism, murder, rape, human trafficking, counterfeit currency) or habitual offenders who pose an imminent escape or violent risk.",
        "key_statutory_ingredients": ["Section 43(3) BNSS", "Heinous offences & repeat offenders", "Exceptions to Prem Shankar Shukla rule"],
        "citation_benchmark": "Prem Shankar Shukla v. Delhi Admn. (1980) 3 SCC 526",
        "complexity": "Intermediate"
    },
    {
        "id": "BNSS-008",
        "category": "Criminal Procedure & Bail",
        "sub_category": "Trial in Absentia",
        "statute": "Bharatiya Nagarik Suraksha Sanhita, 2023",
        "relevant_sections": ["Section 356 BNSS"],
        "question": "What is the procedure for conducting a trial in absentia against proclaimed offenders under Section 356 of BNSS 2023?",
        "ground_truth_context": "Section 356 BNSS provides that when a person declared a proclaimed offender under Section 84 has absconded and there is no immediate prospect of arresting him, the court may proceed with the trial in his absence and pronounce judgment, after issuing consecutive warrants and publishing notices for 90 days.",
        "ground_truth_answer": "Under Section 356 BNSS, if a proclaimed offender absconds to evade trial: (1) The court issues warrants and publishes public proclamations giving 90 days to appear; (2) If the accused fails to appear, the court appoints a state-funded legal aid defense counsel; (3) The entire trial, evidence recording, and judgment proceed in absentia.",
        "key_statutory_ingredients": ["Section 356 BNSS", "90-day notice period", "Court-appointed defense counsel", "Full evidentiary trial in absence"],
        "citation_benchmark": "Statutory Innovation under Section 356 BNSS (w.e.f. July 1, 2024)",
        "complexity": "Advanced"
    },
    {
        "id": "BNSS-009",
        "category": "Criminal Procedure & Bail",
        "sub_category": "Inherent Powers of High Court",
        "statute": "Bharatiya Nagarik Suraksha Sanhita, 2023",
        "relevant_sections": ["Section 528 BNSS"],
        "question": "What is the provision for quashing an FIR or criminal complaint under the inherent powers of the High Court in BNSS 2023?",
        "ground_truth_context": "Section 528 BNSS preserves the inherent powers of the High Court to make such orders as may be necessary to give effect to any order under this Sanhita, or to prevent abuse of the process of any Court or otherwise to secure the ends of justice (equivalent to old Section 482 CrPC).",
        "ground_truth_answer": "Section 528 BNSS preserves the inherent jurisdiction of the High Court to quash an FIR, chargesheet, or summoning order to: (1) Prevent abuse of the judicial process; (2) Secure the ends of justice; or (3) Give effect to orders under the Sanhita, applying Bhajan Lal test principles.",
        "key_statutory_ingredients": ["Section 528 BNSS (formerly 482 CrPC)", "Prevention of abuse of process", "Securing ends of justice"],
        "citation_benchmark": "State of Haryana v. Bhajan Lal 1992 Supp (1) SCC 335",
        "complexity": "Basic"
    },
    {
        "id": "BNSS-010",
        "category": "Criminal Procedure & Bail",
        "sub_category": "Regular Bail in Non-Bailable Offences",
        "statute": "Bharatiya Nagarik Suraksha Sanhita, 2023",
        "relevant_sections": ["Section 480 BNSS", "Section 483 BNSS"],
        "question": "What are the exceptions where a Magistrate may grant regular bail in non-bailable offences punishable with death or life imprisonment under Section 480 BNSS?",
        "ground_truth_context": "Under the first proviso to Section 480(1) BNSS (formerly Section 437(1) CrPC), the Court may direct that a person be released on bail if such person is: (1) Under the age of sixteen years; (2) A woman; or (3) Sick or infirm.",
        "ground_truth_answer": "Under the first proviso to Section 480(1) BNSS, a Magistrate may grant bail even for offences punishable with death or life imprisonment if the accused is: (1) A minor under sixteen years of age; (2) A woman; or (3) Sick or infirm.",
        "key_statutory_ingredients": ["Under 16 years", "Woman", "Sick or infirm person", "Section 480(1) first proviso"],
        "citation_benchmark": "Prahlad Singh Bhati v. NCT, Delhi (2001) 4 SCC 280",
        "complexity": "Intermediate"
    },
    {
        "id": "BNSS-011",
        "category": "Criminal Procedure & Bail",
        "sub_category": "Witness Protection",
        "statute": "Bharatiya Nagarik Suraksha Sanhita, 2023",
        "relevant_sections": ["Section 398 BNSS"],
        "question": "How does Section 398 of BNSS 2023 mandate state governments to protect vulnerable witnesses?",
        "ground_truth_context": "Section 398 BNSS mandates that every State Government shall prepare and notify a Witness Protection Scheme for the State to ensure protection of witnesses in criminal proceedings.",
        "ground_truth_answer": "Section 398 BNSS makes it legally obligatory for every State Government to formulate and notify a comprehensive Witness Protection Scheme, institutionalizing witness identity concealment, relocation, and protection measures.",
        "key_statutory_ingredients": ["Section 398 BNSS", "Mandatory State Witness Protection Scheme", "Statutory codification of Mahender Chawla"],
        "citation_benchmark": "Mahender Chawla v. Union of India (2019) 14 SCC 615",
        "complexity": "Basic"
    },
    {
        "id": "BNSS-012",
        "category": "Criminal Procedure & Bail",
        "sub_category": "Victim Compensation",
        "statute": "Bharatiya Nagarik Suraksha Sanhita, 2023",
        "relevant_sections": ["Section 396 BNSS"],
        "question": "Under what statutory mechanism can interim victim compensation be awarded under Section 396 of BNSS 2023?",
        "ground_truth_context": "Section 396 BNSS stipulates that the court or State/District Legal Services Authority can award compensation to victims of crime for rehabilitation and interim medical expenses even where the trial does not result in conviction or the accused is unidentified.",
        "ground_truth_answer": "Section 396 BNSS empowers courts and DLSA/SLSA to award interim compensation for medical aid and rehabilitation to victims of crime, including sexual assault and acid attack cases, even before the completion of trial or where the offender remains untraced.",
        "key_statutory_ingredients": ["Section 396 BNSS", "Interim compensation via DLSA", "Applies regardless of conviction"],
        "citation_benchmark": "Nipun Saxena v. Union of India (2019) 2 SCC 703",
        "complexity": "Intermediate"
    },

    # ---------------------------------------------------------
    # PILLAR 3: Substantive Criminal Law under Bharatiya Nyaya Sanhita, 2023 (BNS)
    # ---------------------------------------------------------
    {
        "id": "BNS-001",
        "category": "Substantive Criminal Law",
        "sub_category": "Murder and Life Imprisonment",
        "statute": "Bharatiya Nyaya Sanhita, 2023",
        "relevant_sections": ["Section 103(1) BNS", "Section 101 BNS"],
        "question": "What is the punishment for Murder under Section 103(1) of Bharatiya Nyaya Sanhita, 2023?",
        "ground_truth_context": "Section 103(1) BNS provides: Whoever commits murder shall be punished with death or imprisonment for life, and shall also be liable to fine (replacing Section 302 of the Indian Penal Code).",
        "ground_truth_answer": "Under Section 103(1) of the BNS 2023, the prescribed punishment for murder is either death or imprisonment for life, along with a mandatory fine.",
        "key_statutory_ingredients": ["Death or imprisonment for life", "Mandatory fine", "Section 103(1) BNS"],
        "citation_benchmark": "Bachan Singh v. State of Punjab (1980) 2 SCC 684",
        "complexity": "Basic"
    },
    {
        "id": "BNS-002",
        "category": "Substantive Criminal Law",
        "sub_category": "Snatching as Distinct Offence",
        "statute": "Bharatiya Nyaya Sanhita, 2023",
        "relevant_sections": ["Section 304 BNS"],
        "question": "How is 'Snatching' defined and punished under Section 304 of BNS 2023?",
        "ground_truth_context": "Section 304(1) BNS defines snatching: Theft is 'snatching' if, in order to commit theft, the offender suddenly or quickly or forcibly seizes or secures or grabs or takes away from any person or from his possession any movable property. Under Section 304(2), punishment is imprisonment up to three years and fine.",
        "ground_truth_answer": "Section 304 of BNS 2023 creates 'Snatching' as a standalone criminal offence separate from simple theft. It occurs when movable property is seized suddenly, quickly, or forcibly from someone's possession. It is punishable with imprisonment up to 3 years and a fine.",
        "key_statutory_ingredients": ["Section 304 BNS", "Sudden or forcible seizure", "Up to 3 years imprisonment"],
        "citation_benchmark": "Statutory Offence under Section 304 BNS 2023",
        "complexity": "Basic"
    },
    {
        "id": "BNS-003",
        "category": "Substantive Criminal Law",
        "sub_category": "Organized Crime",
        "statute": "Bharatiya Nyaya Sanhita, 2023",
        "relevant_sections": ["Section 111 BNS"],
        "question": "What constitute the statutory ingredients of 'Organized Crime' under Section 111 of BNS 2023?",
        "ground_truth_context": "Section 111 BNS defines organized crime as any continuing unlawful activity including kidnapping, robbery, extortion, land grabbing, contract killing, cybercrime, economic offences, or human trafficking by a member of an organized crime syndicate, using violence, intimidation, or coercion to gain direct or indirect material benefit.",
        "ground_truth_answer": "Under Section 111 BNS, Organized Crime requires: (1) Continuing unlawful activity by an organized crime syndicate; (2) Use of violence, threat of violence, intimidation, or coercion; (3) Objective of obtaining direct or indirect material or financial benefit; (4) If resulting in death of any person, punishment is death or life imprisonment with minimum fine of INR 10 Lakhs.",
        "key_statutory_ingredients": ["Continuing unlawful activity", "Organized crime syndicate", "Death or life imprisonment + INR 10 Lakh fine", "Section 111 BNS"],
        "citation_benchmark": "State of Maharashtra v. Lalit Somdatta Nagpal (2007) 4 SCC 171",
        "complexity": "Advanced"
    },
    {
        "id": "BNS-004",
        "category": "Substantive Criminal Law",
        "sub_category": "Terrorist Act",
        "statute": "Bharatiya Nyaya Sanhita, 2023",
        "relevant_sections": ["Section 113 BNS"],
        "question": "What acts qualify as a 'Terrorist Act' under Section 113 of BNS 2023?",
        "ground_truth_context": "Section 113 BNS defines a terrorist act as any act committed with intent to threaten or likely to threaten the unity, integrity, sovereignty, or security of India, or to intimidate the general public, by using bombs, dynamite, firearms, lethal weapons, or hazardous substances.",
        "ground_truth_answer": "Under Section 113 BNS 2023, a Terrorist Act is any act done with the intent to threaten or likely to threaten the sovereignty, unity, integrity, or security of India, or strike terror in the people, through weapons, explosives, poisonous gases, or cyber attacks. If death results, punishment is death or life imprisonment.",
        "key_statutory_ingredients": ["Threat to unity, integrity, security of India", "Striking terror in public", "Death or life imprisonment", "Section 113 BNS"],
        "citation_benchmark": "Hitendra Vishnu Thakur v. State of Maharashtra (1994) 4 SCC 602",
        "complexity": "Advanced"
    },
    {
        "id": "BNS-005",
        "category": "Substantive Criminal Law",
        "sub_category": "Hit and Run",
        "statute": "Bharatiya Nyaya Sanhita, 2023",
        "relevant_sections": ["Section 106(2) BNS"],
        "question": "What is the enhanced penalty under Section 106(2) BNS for causing death by rash and negligent driving and fleeing the scene?",
        "ground_truth_context": "Section 106(2) BNS stipulates: Whoever causes death of any person by doing any rash or negligent act not amounting to culpable homicide and escapes without reporting it to a police officer or a Magistrate soon after the incident, shall be punished with imprisonment up to ten years and fine.",
        "ground_truth_answer": "Section 106(2) BNS imposes an enhanced sentence of imprisonment up to 10 years and a fine if an offender causes death by rash or negligent driving and escapes the scene without reporting the accident to the police or a Magistrate shortly thereafter.",
        "key_statutory_ingredients": ["Rash and negligent driving death", "Escaping without reporting", "Up to 10 years imprisonment", "Section 106(2) BNS"],
        "citation_benchmark": "Statutory Provision under Section 106(2) BNS 2023",
        "complexity": "Intermediate"
    },
    {
        "id": "BNS-006",
        "category": "Substantive Criminal Law",
        "sub_category": "Deceitful Sexual Intercourse",
        "statute": "Bharatiya Nyaya Sanhita, 2023",
        "relevant_sections": ["Section 69 BNS"],
        "question": "What is the offence of sexual intercourse on false promise of employment or marriage under Section 69 BNS?",
        "ground_truth_context": "Section 69 BNS provides: Whoever, by deceitful means or making by promise to marry unto a woman without any intention of fulfilling the same, has sexual intercourse with her, such sexual intercourse not amounting to the offence of rape, shall be punished with imprisonment up to ten years and fine.",
        "ground_truth_answer": "Section 69 BNS criminalizes sexual intercourse obtained by deceitful means (including false promise of employment, promotion, identity concealment) or making a promise to marry without any bona fide intention of fulfilling it. It is punishable with imprisonment up to 10 years and a fine.",
        "key_statutory_ingredients": ["Deceitful means or false promise to marry", "No intention to marry at inception", "Imprisonment up to 10 years", "Section 69 BNS"],
        "citation_benchmark": "Anurag Soni v. State of Chhattisgarh (2019) 10 SCC 660",
        "complexity": "Advanced"
    },
    {
        "id": "BNS-007",
        "category": "Substantive Criminal Law",
        "sub_category": "Mob Lynching",
        "statute": "Bharatiya Nyaya Sanhita, 2023",
        "relevant_sections": ["Section 103(2) BNS"],
        "question": "What provision of BNS 2023 specifically punishes mob lynching and hate-motivated murder by groups?",
        "ground_truth_context": "Section 103(2) BNS provides that when a group of five or more persons acting in concert commits murder on the ground of race, caste or community, sex, place of birth, language, personal belief or any other ground, each member shall be punished with death or imprisonment for life, and fine.",
        "ground_truth_answer": "Section 103(2) BNS codifies mob lynching: When a group of 5 or more persons acting together commits murder on grounds of race, caste, community, religion, gender, or personal belief, every member of that group is punished with death or life imprisonment and fine.",
        "key_statutory_ingredients": ["Group of five or more", "Murder on grounds of race, caste, community", "Death or life imprisonment", "Section 103(2) BNS"],
        "citation_benchmark": "Tehseen S. Poonawalla v. Union of India (2018) 9 SCC 501",
        "complexity": "Intermediate"
    },
    {
        "id": "BNS-008",
        "category": "Substantive Criminal Law",
        "sub_category": "Cheating and Inducing Delivery",
        "statute": "Bharatiya Nyaya Sanhita, 2023",
        "relevant_sections": ["Section 318(4) BNS"],
        "question": "What constitutes Cheating under Section 318(4) BNS (formerly Section 420 IPC)?",
        "ground_truth_context": "Section 318(4) BNS states: Whoever cheats and thereby dishonestly induces the person deceived to deliver any property to any person, or to make, alter or destroy the whole or any part of a valuable security, shall be punished with imprisonment up to seven years, and fine.",
        "ground_truth_answer": "Under Section 318(4) BNS 2023, the ingredients are: (1) Deception of a person; (2) Dishonestly inducing that person to deliver property or alter a valuable security; (3) Fraudulent or dishonest intent existing at the very inception of the transaction. Punishment is imprisonment up to 7 years and fine.",
        "key_statutory_ingredients": ["Dishonest inducement", "Delivery of property", "Imprisonment up to 7 years", "Section 318(4) BNS"],
        "citation_benchmark": "Hridaya Ranjan Prasad Verma v. State of Bihar (2000) 4 SCC 168",
        "complexity": "Basic"
    },
    {
        "id": "BNS-009",
        "category": "Substantive Criminal Law",
        "sub_category": "Criminal Breach of Trust",
        "statute": "Bharatiya Nyaya Sanhita, 2023",
        "relevant_sections": ["Section 316 BNS"],
        "question": "What is Criminal Breach of Trust under Section 316 of BNS 2023, and how does it differ from cheating?",
        "ground_truth_context": "Section 316 BNS requires entrustment of property or dominion over property, followed by dishonest misappropriation or conversion to own use. In cheating (Section 318), dishonest inducement starts at the inception, whereas in CBT (Section 316), possession is initially acquired lawfully through entrustment.",
        "ground_truth_answer": "Under Section 316 BNS, Criminal Breach of Trust requires: (1) Entrustment with property; (2) Dishonest misappropriation or conversion to one's own use in violation of legal mandate. The key difference from Cheating (Sec 318) is that CBT begins with lawful entrustment, while Cheating begins with fraudulent inducement from the start.",
        "key_statutory_ingredients": ["Lawful entrustment", "Subsequent dishonest misappropriation", "Section 316 BNS"],
        "citation_benchmark": "Rashmi Kumar v. Mahesh Kumar Bhada (1997) 2 SCC 397",
        "complexity": "Intermediate"
    },
    {
        "id": "BNS-010",
        "category": "Substantive Criminal Law",
        "sub_category": "Defamation and Community Service",
        "statute": "Bharatiya Nyaya Sanhita, 2023",
        "relevant_sections": ["Section 356 BNS"],
        "question": "What is the penalty for Criminal Defamation under Section 356 BNS, and what novel punishment is introduced?",
        "ground_truth_context": "Section 356(2) BNS provides that whoever defames another shall be punished with simple imprisonment for a term which may extend to two years, or with fine, or with both, or with community service.",
        "ground_truth_answer": "Under Section 356(2) BNS 2023, criminal defamation is punishable with simple imprisonment up to 2 years, fine, or both, or with the newly introduced non-custodial punishment of **Community Service**.",
        "key_statutory_ingredients": ["Section 356 BNS", "Up to 2 years simple imprisonment", "Community Service alternative"],
        "citation_benchmark": "Subramanian Swamy v. Union of India (2016) 7 SCC 221",
        "complexity": "Basic"
    },

    # ---------------------------------------------------------
    # PILLAR 4: Evidence & Forensics under Bharatiya Sakshya Adhiniyam, 2023 (BSA)
    # ---------------------------------------------------------
    {
        "id": "BSA-001",
        "category": "Law of Evidence",
        "sub_category": "Electronic Evidence Certificate",
        "statute": "Bharatiya Sakshya Adhiniyam, 2023",
        "relevant_sections": ["Section 63 BSA"],
        "question": "What are the legal requirements for admissibility of electronic records and certificates under Section 63 of BSA 2023?",
        "ground_truth_context": "Section 63 BSA (replacing Section 65B of Indian Evidence Act) governs admissibility of electronic records. Section 63(4) requires a certificate signed by a person in charge of the management of the device or an expert, identifying the electronic record and describing the device.",
        "ground_truth_answer": "Under Section 63 BSA 2023, secondary electronic evidence (printouts, call records, CCTV footage) is admissible only when accompanied by a statutory Certificate under Section 63(4), signed by the custodian in lawful control of the computer/device or a certified expert, verifying device integrity during the relevant period.",
        "key_statutory_ingredients": ["Section 63(4) BSA certificate", "Custodian in lawful management", "Statutory condition precedent"],
        "citation_benchmark": "Arjun Panditrao Khotkar v. Kailash Kushanrao Gorantyal (2020) 7 SCC 1",
        "complexity": "Advanced"
    },
    {
        "id": "BSA-002",
        "category": "Law of Evidence",
        "sub_category": "Primary vs Secondary Digital Evidence",
        "statute": "Bharatiya Sakshya Adhiniyam, 2023",
        "relevant_sections": ["Section 57 BSA", "Section 58 BSA"],
        "question": "Is a certificate under Section 63 BSA required if the original digital storage medium itself is produced before the court?",
        "ground_truth_context": "Under Section 57 BSA Explanation 4 & 5, where electronic record is produced from proper custody as primary evidence (the actual original phone, hard disk, or memory card), production of Section 63 certificate is unnecessary.",
        "ground_truth_answer": "No. When the original electronic hardware (the smartphone, server hard disk, or memory card itself) is produced directly before the Court as Primary Evidence under Section 57 BSA, a Section 63 certificate is not mandatory; the certificate is required only when producing Secondary electronic copies.",
        "key_statutory_ingredients": ["Section 57 BSA Primary Evidence", "Original hardware production", "No Sec 63 certificate needed for primary"],
        "citation_benchmark": "Arjun Panditrao Khotkar v. Kailash Kushanrao Gorantyal (2020) 7 SCC 1",
        "complexity": "Advanced"
    },
    {
        "id": "BSA-003",
        "category": "Law of Evidence",
        "sub_category": "Confessions to Police",
        "statute": "Bharatiya Sakshya Adhiniyam, 2023",
        "relevant_sections": ["Section 23(1) BSA"],
        "question": "Are confessions made to a police officer admissible as evidence in a criminal trial under BSA 2023?",
        "ground_truth_context": "Section 23(1) BSA provides that no confession made to a police officer shall be proved as against a person accused of any offence.",
        "ground_truth_answer": "No. Under Section 23(1) of the Bharatiya Sakshya Adhiniyam 2023 (formerly Section 25 Evidence Act), any confession made to a police officer is completely inadmissible as evidence against the accused.",
        "key_statutory_ingredients": ["Section 23(1) BSA", "Total inadmissibility of police confession", "Protection against police coercion"],
        "citation_benchmark": "Aghnoo Nagesia v. State of Bihar AIR 1966 SC 119",
        "complexity": "Basic"
    },
    {
        "id": "BSA-004",
        "category": "Law of Evidence",
        "sub_category": "Information Leading to Discovery",
        "statute": "Bharatiya Sakshya Adhiniyam, 2023",
        "relevant_sections": ["Section 23(2) BSA proviso"],
        "question": "What part of an accused's disclosure statement to police is admissible under Section 23(2) of BSA 2023?",
        "ground_truth_context": "Under the proviso to Section 23(2) BSA (formerly Section 27 Evidence Act), when any fact is deposed to as discovered in consequence of information received from a person accused of any offence in custody of a police officer, so much of such information, whether it amounts to a confession or not, as relates distinctly to the fact thereby discovered, may be proved.",
        "ground_truth_answer": "Under the proviso to Section 23(2) BSA, only that exact portion of the accused's statement that distinctly relates to the discovery of a tangible physical fact (weapon, stolen property, dead body) is admissible; any confessional statement regarding past guilt remains inadmissible.",
        "key_statutory_ingredients": ["Distinct discovery of tangible fact", "Section 23(2) BSA proviso (formerly Sec 27 IEA)", "Pulukuri Kottaya principle"],
        "citation_benchmark": "Pulukuri Kottaya v. Emperor AIR 1947 PC 67",
        "complexity": "Advanced"
    },
    {
        "id": "BSA-005",
        "category": "Law of Evidence",
        "sub_category": "Dying Declaration",
        "statute": "Bharatiya Sakshya Adhiniyam, 2023",
        "relevant_sections": ["Section 26(a) BSA"],
        "question": "Can a conviction be based solely on an uncorroborated Dying Declaration under Section 26(a) BSA 2023?",
        "ground_truth_context": "Section 26(a) BSA makes statements written or verbal of relevant facts made by a person who is dead admissible when the statement relates to the cause of his death. If found truthful and voluntary, it can form the sole basis of conviction.",
        "ground_truth_answer": "Yes. A dying declaration under Section 26(a) BSA can form the sole basis of conviction without corroboration, provided the court is satisfied that the statement is truthful, voluntary, and made by the deceased in a fit mental state.",
        "key_statutory_ingredients": ["Cause of death", "Fit state of mind", "Sole basis of conviction permitted", "Section 26(a) BSA"],
        "citation_benchmark": "Laxman v. State of Maharashtra (2002) 6 SCC 710",
        "complexity": "Intermediate"
    },
    {
        "id": "BSA-006",
        "category": "Law of Evidence",
        "sub_category": "Presumption of Abetment of Suicide of Wife",
        "statute": "Bharatiya Sakshya Adhiniyam, 2023",
        "relevant_sections": ["Section 117 BSA"],
        "question": "When does the court draw a presumption of abetment of suicide of a married woman under Section 117 BSA?",
        "ground_truth_context": "Section 117 BSA provides that when a woman commits suicide within seven (7) years of marriage and it is shown that her husband or his relative subjected her to cruelty, the Court may presume that such suicide was abetted by her husband or relative.",
        "ground_truth_answer": "Under Section 117 BSA (formerly Section 113A IEA): (1) The suicide occurred within 7 years of marriage; (2) The woman was subjected to cruelty by her husband or his relatives. Upon proving these two prerequisites, the court may presume abetment of suicide.",
        "key_statutory_ingredients": ["Within 7 years of marriage", "Proof of cruelty", "Discretionary presumption", "Section 117 BSA"],
        "citation_benchmark": "Ramesh Kumar v. State of Chhattisgarh (2001) 9 SCC 618",
        "complexity": "Intermediate"
    },
    {
        "id": "BSA-007",
        "category": "Law of Evidence",
        "sub_category": "Presumption of Dowry Death",
        "statute": "Bharatiya Sakshya Adhiniyam, 2023",
        "relevant_sections": ["Section 118 BSA"],
        "question": "What is the statutory presumption as to Dowry Death under Section 118 BSA, and is it mandatory?",
        "ground_truth_context": "Section 118 BSA provides that when the question is whether a person has committed the dowry death of a woman and it is shown that soon before her death she was subjected to cruelty or harassment for dowry, the Court shall presume that such person had caused the dowry death.",
        "ground_truth_answer": "Under Section 118 BSA (formerly Section 113B IEA), the presumption is **mandatory ('shall presume')**. Once the prosecution proves that the woman died within 7 years of marriage under abnormal circumstances and was subjected to cruelty for dowry demands 'soon before death', the court must presume dowry death unless rebutted.",
        "key_statutory_ingredients": ["Mandatory 'shall presume'", "Cruelty 'soon before death'", "Within 7 years of marriage", "Section 118 BSA"],
        "citation_benchmark": "Satbir Singh v. State of Haryana (2021) 6 SCC 1",
        "complexity": "Intermediate"
    },
    {
        "id": "BSA-008",
        "category": "Law of Evidence",
        "sub_category": "Expert Opinion on Digital Signatures",
        "statute": "Bharatiya Sakshya Adhiniyam, 2023",
        "relevant_sections": ["Section 39 BSA", "Section 40 BSA"],
        "question": "How is expert opinion on electronic signatures and digital forensic records admitted under Section 39 BSA?",
        "ground_truth_context": "Section 39 BSA provides that when the Court has to form an opinion upon a point of foreign law, science, art, or as to identity of handwriting, finger impressions, or electronic signatures, the opinions of persons specially skilled are relevant facts.",
        "ground_truth_answer": "Under Section 39 BSA 2023, the opinion of the Examiner of Electronic Evidence (notified under Section 79A IT Act) is a relevant expert fact to prove the authenticity of digital signatures, hash integrity, and computer forensic artifacts.",
        "key_statutory_ingredients": ["Section 39 BSA", "Section 79A IT Act examiner", "Electronic signature identity"],
        "citation_benchmark": "Statutory Provision under Section 39 BSA 2023",
        "complexity": "Intermediate"
    },

    # ---------------------------------------------------------
    # PILLAR 5: Constitutional Law & Writs
    # ---------------------------------------------------------
    {
        "id": "CONST-001",
        "category": "Constitutional Law",
        "sub_category": "Writ of Habeas Corpus",
        "statute": "Constitution of India",
        "relevant_sections": ["Article 32", "Article 226"],
        "question": "When can a Writ of Habeas Corpus be filed under Article 32 or 226 of the Constitution of India?",
        "ground_truth_context": "A writ of Habeas Corpus lies against unlawful or without legal authority detention of any person by state authorities or private individuals, directing the detaining authority to produce the body of the person before the court.",
        "ground_truth_answer": "A Writ of Habeas Corpus is filed under Article 32 (Supreme Court) or Article 226 (High Court) whenever a person is illegally or without authority of law detained or imprisoned. The court commands the detaining authority to produce the detenue and set them free if detention lacks lawful basis.",
        "key_statutory_ingredients": ["Article 32 / 226", "Illegal detention", "Production of body of person"],
        "citation_benchmark": "Sunil Batra v. Delhi Administration (1980) 3 SCC 488",
        "complexity": "Basic"
    },
    {
        "id": "CONST-002",
        "category": "Constitutional Law",
        "sub_category": "Right to Privacy",
        "statute": "Constitution of India",
        "relevant_sections": ["Article 21"],
        "question": "What is the three-fold proportionality test established in K.S. Puttaswamy for state encroachment on Right to Privacy under Article 21?",
        "ground_truth_context": "The 9-judge bench in Puttaswamy held that privacy is a fundamental right under Article 21. Any state restriction must satisfy: (1) Legality (backed by statutory law); (2) Legitimate state aim / necessity; (3) Proportionality (least intrusive means).",
        "ground_truth_answer": "Under the 9-judge bench ruling in K.S. Puttaswamy: (1) Legality: An explicit legislative law must exist; (2) Legitimate Aim: The encroachment must serve a necessary state purpose; (3) Proportionality: The rational nexus between objects and means, adopting the least restrictive measure.",
        "key_statutory_ingredients": ["Article 21 fundamental right", "Legality, Legitimate State Aim, Proportionality", "Puttaswamy 9-judge bench"],
        "citation_benchmark": "K.S. Puttaswamy v. Union of India (2017) 10 SCC 1",
        "complexity": "Advanced"
    },
    {
        "id": "CONST-003",
        "category": "Constitutional Law",
        "sub_category": "Article 14 Equality & Non-Arbitrariness",
        "statute": "Constitution of India",
        "relevant_sections": ["Article 14"],
        "question": "What is the 'Manifest Arbitrariness' test under Article 14 of the Constitution of India?",
        "ground_truth_context": "Shayara Bano and Navtej Johar established that legislation or executive action can be struck down under Article 14 for 'manifest arbitrariness' if it is done capriciously, irrationally, or without adequate determining principle.",
        "ground_truth_answer": "Under Article 14, 'Manifest Arbitrariness' means something done arbitrarily, irrationally, without an adequate determining principle, or caprice. A law or executive act suffering from manifest arbitrariness violates the guarantee of equality and is void.",
        "key_statutory_ingredients": ["Article 14", "Manifest arbitrariness doctrine", "Lack of determining principle"],
        "citation_benchmark": "Shayara Bano v. Union of India (2017) 9 SCC 1",
        "complexity": "Advanced"
    },
    {
        "id": "CONST-004",
        "category": "Constitutional Law",
        "sub_category": "Self-Incrimination and Lie Detectors",
        "statute": "Constitution of India",
        "relevant_sections": ["Article 20(3)"],
        "question": "Are involuntary narco-analysis, polygraph, and brain-mapping tests constitutional under Article 20(3)?",
        "ground_truth_context": "The Supreme Court in Selvi held that compulsory administration of narco-analysis, polygraph, and BEAP tests violates the rule against self-incrimination under Article 20(3) and the right to personal liberty under Article 21.",
        "ground_truth_answer": "No. In Selvi v. State of Karnataka, the Supreme Court held that conducting involuntary narco-analysis, polygraph, or brain electrical activation tests on an accused violates Article 20(3) (Protection against self-incrimination) and the substantive due process aspect of Article 21.",
        "key_statutory_ingredients": ["Article 20(3)", "Mental privacy under Art 21", "Involuntary scientific tests prohibited"],
        "citation_benchmark": "Selvi v. State of Karnataka (2010) 7 SCC 263",
        "complexity": "Intermediate"
    },
    {
        "id": "CONST-005",
        "category": "Constitutional Law",
        "sub_category": "Double Jeopardy",
        "statute": "Constitution of India",
        "relevant_sections": ["Article 20(2)"],
        "question": "What are the essential elements required to invoke protection against Double Jeopardy under Article 20(2)?",
        "ground_truth_context": "Article 20(2) provides: No person shall be prosecuted and punished for the same offence more than once. It applies only where the previous prosecution and punishment were before a court of law or judicial tribunal.",
        "ground_truth_answer": "To claim protection under Article 20(2): (1) There must have been a previous prosecution before a court of law or judicial tribunal; (2) The accused must have been punished in that prosecution; (3) The second prosecution must be for the exact same offence. Departmental or disciplinary proceedings do not bar criminal prosecution.",
        "key_statutory_ingredients": ["Prosecuted and punished", "Same offence", "Court or judicial tribunal", "Article 20(2)"],
        "citation_benchmark": "Maqbool Hussain v. State of Bombay AIR 1953 SC 325",
        "complexity": "Intermediate"
    },
    {
        "id": "CONST-006",
        "category": "Constitutional Law",
        "sub_category": "Writ of Mandamus",
        "statute": "Constitution of India",
        "relevant_sections": ["Article 226"],
        "question": "What conditions must be satisfied before a High Court issues a Writ of Mandamus under Article 226?",
        "ground_truth_context": "A Writ of Mandamus is an order commanding a public authority or person to perform a public or statutory duty. The petitioner must have a clear legal right to demand performance, and the respondent must have a corresponding statutory obligation that was neglected despite demand.",
        "ground_truth_answer": "For Mandamus: (1) Petitioner must have a legally enforceable right; (2) The respondent must owe a mandatory public/statutory duty (not discretionary); (3) Petitioner must have made a prior demand for performance which was refused or ignored by the authority.",
        "key_statutory_ingredients": ["Mandatory public duty", "Clear legal right", "Prior demand and refusal"],
        "citation_benchmark": "Mani Subrat Jain v. State of Haryana (1977) 1 SCC 486",
        "complexity": "Intermediate"
    },
    {
        "id": "CONST-007",
        "category": "Constitutional Law",
        "sub_category": "Freedom of Speech and Internet",
        "statute": "Constitution of India",
        "relevant_sections": ["Article 19(1)(a)", "Article 19(2)"],
        "question": "Is access to internet protected under Article 19(1)(a), and can internet shutdowns be indefinite?",
        "ground_truth_context": "In Anuradha Bhasin, the Supreme Court ruled that freedom of speech and expression and the freedom to practice any profession over the internet are constitutionally protected under Article 19(1)(a) and 19(1)(g). Indefinite suspension of internet services is illegal.",
        "ground_truth_answer": "Yes. In Anuradha Bhasin v. Union of India, the Supreme Court held that the right to speech and trade via the medium of internet is protected under Article 19(1)(a) and 19(1)(g). Indefinite suspension of internet is unconstitutional; shutdown orders must be periodic, published, and satisfy the proportionality test.",
        "key_statutory_ingredients": ["Article 19(1)(a) internet rights", "Indefinite shutdown illegal", "Proportionality review"],
        "citation_benchmark": "Anuradha Bhasin v. Union of India (2020) 3 SCC 637",
        "complexity": "Intermediate"
    },
    {
        "id": "CONST-008",
        "category": "Constitutional Law",
        "sub_category": "Writ of Quo Warranto",
        "statute": "Constitution of India",
        "relevant_sections": ["Article 226"],
        "question": "Against whom does a Writ of Quo Warranto lie and what must the petitioner establish?",
        "ground_truth_context": "A writ of Quo Warranto challenges an unauthorized usurpation of a public office. The petitioner must show that the office is of a public nature created by statute/Constitution, and that the incumbent does not possess the requisite statutory qualifications.",
        "ground_truth_answer": "Quo Warranto lies to oust an usurper from a substantive public office. The petitioner must establish that: (1) The office is a public office created by statute or Constitution; (2) The incumbent holding the office lacks statutory eligibility criteria or was appointed in violation of mandatory statutory rules.",
        "key_statutory_ingredients": ["Substantive public office", "Usurpation without statutory eligibility", "Locus standi is open"],
        "citation_benchmark": "Central Electricity Supply Utility of Odisha v. Dhobei Sahoo (2014) 1 SCC 161",
        "complexity": "Intermediate"
    },

    # ---------------------------------------------------------
    # PILLAR 6: Civil Procedure & Remedies (CPC 1908 & SRA 1963)
    # ---------------------------------------------------------
    {
        "id": "CPC-001",
        "category": "Civil Procedure & Remedies",
        "sub_category": "Rejection of Plaint",
        "statute": "Code of Civil Procedure, 1908",
        "relevant_sections": ["Order VII Rule 11 CPC"],
        "question": "What are the grounds for rejection of a plaint under Order VII Rule 11 CPC, and can the court look into the written statement?",
        "ground_truth_context": "Order VII Rule 11 lists grounds including: (a) where it does not disclose a cause of action; (d) where the suit appears from the statement in the plaint to be barred by any law. It is settled law that only the averments in the plaint can be looked into, not the defence in the written statement.",
        "ground_truth_answer": "Order VII Rule 11 CPC permits rejection of a plaint if: (1) No cause of action is disclosed; (2) Relief is undervalued; (3) Insufficiently stamped; (4) Suit is barred by any law (limitation, res judicata on face of plaint). Crucially, the court can look **only at the plaint averments and documents annexed thereto**, without looking into the defendant's written statement.",
        "key_statutory_ingredients": ["Order 7 Rule 11 CPC", "No cause of action or barred by law", "Only plaint averments considered"],
        "citation_benchmark": "Dahiben v. Arvindbhai Kalyanji Bhanusali (2020) 7 SCC 366",
        "complexity": "Intermediate"
    },
    {
        "id": "CPC-002",
        "category": "Civil Procedure & Remedies",
        "sub_category": "Temporary Injunctions",
        "statute": "Code of Civil Procedure, 1908",
        "relevant_sections": ["Order XXXIX Rules 1 and 2 CPC"],
        "question": "What are the three cardinal tests for grant of a temporary injunction under Order 39 Rules 1 and 2 CPC?",
        "ground_truth_context": "Grant of temporary injunction under Order XXXIX requires satisfaction of three cumulative conditions: (1) Prima facie case; (2) Balance of convenience; (3) Irreparable injury which cannot be compensated in terms of money.",
        "ground_truth_answer": "To obtain a temporary injunction under Order 39 Rules 1 & 2 CPC, the plaintiff must concurrently establish: (1) **Prima facie case**: A substantial question to be investigated; (2) **Balance of convenience**: Greater hardship to plaintiff if injunction is denied; (3) **Irreparable injury**: Loss that cannot be remedied by monetary damages.",
        "key_statutory_ingredients": ["Prima facie case", "Balance of convenience", "Irreparable loss", "Order 39 Rules 1 & 2 CPC"],
        "citation_benchmark": "Dalpat Kumar v. Prahlad Singh (1992) 1 SCC 719",
        "complexity": "Basic"
    },
    {
        "id": "CPC-003",
        "category": "Civil Procedure & Remedies",
        "sub_category": "Res Judicata",
        "statute": "Code of Civil Procedure, 1908",
        "relevant_sections": ["Section 11 CPC"],
        "question": "What conditions are mandatory to bar a subsequent suit by the Doctrine of Res Judicata under Section 11 CPC?",
        "ground_truth_context": "Section 11 bars trial of any suit or issue in which the matter directly and substantially in issue has been directly and substantially in issue in a former suit between the same parties, litigating under the same title, in a Court competent to try such subsequent suit, and has been heard and finally decided.",
        "ground_truth_answer": "Under Section 11 CPC, Res Judicata requires: (1) Matter directly and substantially in issue must be identical; (2) Same parties or parties litigating under the same title; (3) Former court must have been competent to try the subsequent suit; (4) The issue must have been heard and **finally decided** on merits.",
        "key_statutory_ingredients": ["Directly and substantially in issue", "Same parties / same title", "Competent court", "Heard and finally decided", "Section 11 CPC"],
        "citation_benchmark": "Satyadhyan Ghosal v. Deorajin Debi AIR 1960 SC 941",
        "complexity": "Intermediate"
    },
    {
        "id": "CPC-004",
        "category": "Civil Procedure & Remedies",
        "sub_category": "Setting Aside Ex-Parte Decree",
        "statute": "Code of Civil Procedure, 1908",
        "relevant_sections": ["Order IX Rule 13 CPC"],
        "question": "On what grounds can a defendant apply to set aside an ex-parte decree under Order IX Rule 13 CPC?",
        "ground_truth_context": "Order IX Rule 13 provides that a defendant against whom an ex parte decree is passed may apply to the Court to set it aside; and if he satisfies the Court that the summons was not duly served, or that he was prevented by any sufficient cause from appearing, the Court shall make an order setting aside the decree.",
        "ground_truth_answer": "Under Order 9 Rule 13 CPC, an ex-parte decree can be set aside if the defendant proves: (1) Summons was not duly served on them; OR (2) They were prevented by any 'sufficient cause' (e.g. hospitalization, natural disaster) from appearing when the suit was called for hearing.",
        "key_statutory_ingredients": ["Order 9 Rule 13 CPC", "Summons not duly served", "Sufficient cause for non-appearance"],
        "citation_benchmark": "G.P. Srivastava v. R.K. Raizada (2000) 3 SCC 54",
        "complexity": "Basic"
    },
    {
        "id": "CPC-005",
        "category": "Civil Procedure & Remedies",
        "sub_category": "Second Appeal Jurisdiction",
        "statute": "Code of Civil Procedure, 1908",
        "relevant_sections": ["Section 100 CPC"],
        "question": "What is the jurisdictional threshold for the High Court to entertain a Second Appeal under Section 100 CPC?",
        "ground_truth_context": "Section 100 CPC provides that an appeal shall lie to the High Court from every decree passed in appeal by any Court subordinate to the High Court, if the High Court is satisfied that the case involves a substantial question of law.",
        "ground_truth_answer": "Under Section 100 CPC, a Second Appeal lies before the High Court exclusively upon a **Substantial Question of Law** formulated in the memo of appeal and framed by the High Court. Pure questions of fact or concurrent findings of fact cannot be reopened unless perversity is established.",
        "key_statutory_ingredients": ["Substantial question of law", "Framing of question mandatory", "No reappreciation of pure facts", "Section 100 CPC"],
        "citation_benchmark": "Nazir Mohamed v. J. Kamala (2020) 19 SCC 57",
        "complexity": "Intermediate"
    },
    {
        "id": "CPC-006",
        "category": "Civil Procedure & Remedies",
        "sub_category": "Mandatory Specific Performance",
        "statute": "Specific Relief Act, 1963",
        "relevant_sections": ["Section 10 SRA"],
        "question": "How did the 2018 amendment to Section 10 of the Specific Relief Act alter the court's discretion in granting Specific Performance of a contract?",
        "ground_truth_context": "The 2018 amendment substituted Section 10, changing 'specific performance may, in the discretion of the court, be enforced' to 'specific performance of a contract shall be enforced by the court subject to the provisions contained in sub-section (2) of section 11, section 14 and section 16'.",
        "ground_truth_answer": "The 2018 amendment transformed specific performance from a discretionary equitable remedy into a **mandatory statutory right ('shall be enforced')**. Courts must grant specific performance unless the contract falls under express statutory disqualifications in Sections 11(2), 14, or 16.",
        "key_statutory_ingredients": ["Mandatory remedy ('shall be enforced')", "Removal of judicial discretion", "Section 10 SRA 2018 amendment"],
        "citation_benchmark": "B. Santoshamma v. D. Sarala (2020) 19 SCC 80",
        "complexity": "Intermediate"
    },
    {
        "id": "CPC-007",
        "category": "Civil Procedure & Remedies",
        "sub_category": "Summary Suit for Possession",
        "statute": "Specific Relief Act, 1963",
        "relevant_sections": ["Section 6 SRA"],
        "question": "What are the rules and limitation period for a summary suit for recovery of possession of immovable property under Section 6 of the Specific Relief Act?",
        "ground_truth_context": "Section 6 SRA provides that if any person is dispossessed without his consent of immovable property otherwise than in due course of law, he may recover possession by suit, notwithstanding any other title. No suit under this section shall be brought after the expiry of six months from dispossession or against the Government.",
        "ground_truth_answer": "Under Section 6 SRA: (1) A person dispossessed without consent and otherwise than in due course of law can file a summary suit for possession regardless of title; (2) The suit must be filed within 6 months of dispossession; (3) No such suit lies against the Government; (4) No appeal or review lies against the decree.",
        "key_statutory_ingredients": ["Possession regardless of title", "Within 6 months", "No suit against Government", "Section 6 SRA"],
        "citation_benchmark": "ITC Ltd. v. Adarsh Cooperative Housing Society Ltd. (2013) 10 SCC 169",
        "complexity": "Intermediate"
    },
    {
        "id": "CPC-008",
        "category": "Civil Procedure & Remedies",
        "sub_category": "Execution of Foreign Decrees",
        "statute": "Code of Civil Procedure, 1908",
        "relevant_sections": ["Section 13 CPC", "Section 44A CPC"],
        "question": "Under Section 44A CPC, how can a decree from a reciprocating foreign territory be executed in India, subject to Section 13?",
        "ground_truth_context": "Section 44A allows execution of certified copies of decrees of superior courts of reciprocating territories directly as if passed by a District Court in India, provided the decree is not conclusive under Section 13 (e.g. not pronounced by competent court, or not on merits).",
        "ground_truth_answer": "Under Section 44A CPC, a decree from a notified reciprocating territory (e.g. UK, UAE, Singapore) can be filed directly in an Indian District Court for execution as an Indian decree. However, it can be resisted if it violates any exception under Section 13 (not on merits, founded on breach of Indian law, or violating natural justice).",
        "key_statutory_ingredients": ["Section 44A CPC execution", "Reciprocating territory", "Section 13 exceptions"],
        "citation_benchmark": "Alcon Electronics Pvt. Ltd. v. Celem S.A. (2017) 2 SCC 253",
        "complexity": "Advanced"
    },

    # ---------------------------------------------------------
    # PILLAR 7: Commercial, Arbitration & Insolvency
    # ---------------------------------------------------------
    {
        "id": "ARB-001",
        "category": "Commercial & Arbitration",
        "sub_category": "Interim Measures by Court vs Tribunal",
        "statute": "Arbitration and Conciliation Act, 1996",
        "relevant_sections": ["Section 9", "Section 17"],
        "question": "Can a party approach a Court under Section 9 for interim measures once the Arbitral Tribunal has already been constituted?",
        "ground_truth_context": "Section 9(3) provides that once the arbitral tribunal has been constituted, the Court shall not entertain an application under sub-section (1), unless the Court finds that circumstances exist which may not render the remedy provided under section 17 efficacious.",
        "ground_truth_answer": "Under Section 9(3) of the Arbitration Act, once the Arbitral Tribunal is constituted, the court cannot entertain a Section 9 application unless the applicant proves that the remedy before the arbitral tribunal under Section 17 would be inefficacious (e.g. emergency third-party orders).",
        "key_statutory_ingredients": ["Section 9(3) bar", "Tribunal primacy under Sec 17", "Inefficacious remedy exception"],
        "citation_benchmark": "ArcelorMittal Nippon Steel (India) Ltd. v. Essar Bulk Terminal Ltd. (2022) 1 SCC 712",
        "complexity": "Advanced"
    },
    {
        "id": "ARB-002",
        "category": "Commercial & Arbitration",
        "sub_category": "Setting Aside Arbitral Award",
        "statute": "Arbitration and Conciliation Act, 1996",
        "relevant_sections": ["Section 34(2)", "Section 34(2A)"],
        "question": "What is the scope of 'Patent Illegality' for setting aside a domestic arbitral award under Section 34(2A)?",
        "ground_truth_context": "Section 34(2A) allows setting aside of an arbitral award arising out of arbitrations other than international commercial arbitrations on the ground of patent illegality appearing on the face of the award, provided it is not mere erroneous application of the law or reappreciation of evidence.",
        "ground_truth_answer": "Under Section 34(2A), a domestic arbitral award can be set aside for 'Patent Illegality' only if the illegality goes to the root of the matter (e.g. rewriting terms of contract, perversity, acting contrary to fundamental policy of Indian law). The court cannot act as an appellate court or reappreciate evidence.",
        "key_statutory_ingredients": ["Patent illegality goes to root", "No reappreciation of evidence", "Section 34(2A) domestic awards"],
        "citation_benchmark": "Ssangyong Engineering & Construction Co. Ltd. v. NHAI (2019) 15 SCC 131",
        "complexity": "Advanced"
    },
    {
        "id": "ARB-003",
        "category": "Commercial & Arbitration",
        "sub_category": "Appointment of Arbitrators",
        "statute": "Arbitration and Conciliation Act, 1996",
        "relevant_sections": ["Section 11(6)"],
        "question": "What is the scope of judicial examination by the referral court under Section 11(6) of the Arbitration Act?",
        "ground_truth_context": "Under Section 11(6A) read with Vidya Drolia and In Re: Interplay, the referral court's examination is confined to the prima facie existence of an arbitration agreement. All complex questions of arbitrability, limitation, and merits are left to the arbitral tribunal.",
        "ground_truth_answer": "Under Section 11(6) read with Section 11(6A), the jurisdiction of the Supreme Court or High Court is restricted to a **prima facie examination of the existence of the arbitration agreement**. The court follows the principle of 'When in doubt, refer' (competence-competence).",
        "key_statutory_ingredients": ["Prima facie existence of arbitration agreement", "Competence-competence", "Section 11(6A)"],
        "citation_benchmark": "In Re: Interplay Between Arbitration Agreements & Stamp Act 2023 INSC 1066",
        "complexity": "Advanced"
    },
    {
        "id": "IBC-001",
        "category": "Insolvency and Bankruptcy Code",
        "sub_category": "Financial Creditor CIRP",
        "statute": "Insolvency and Bankruptcy Code, 2016",
        "relevant_sections": ["Section 7 IBC"],
        "question": "What must a Financial Creditor prove before the NCLT to initiate CIRP under Section 7 of IBC 2016?",
        "ground_truth_context": "Under Section 7 IBC, a financial creditor can initiate CIRP when a default of at least INR 1 Crore has occurred. The Adjudicating Authority (NCLT) must satisfy itself regarding the existence of a 'financial debt' and 'default' within 14 days.",
        "ground_truth_answer": "To initiate Corporate Insolvency Resolution Process (CIRP) under Section 7 IBC: (1) Minimum default threshold of INR 1 Crore; (2) Establishing that the debt is a 'financial debt' disbursal against consideration for time value of money; (3) Proof of default (via NeSL record or bank statements). Once debt and default are established, admission is virtually mandatory.",
        "key_statutory_ingredients": ["Threshold of INR 1 Crore", "Financial debt + default", "Section 7 IBC", "Innoventive Industries rule"],
        "citation_benchmark": "Innoventive Industries Ltd. v. ICICI Bank (2018) 1 SCC 407",
        "complexity": "Intermediate"
    },
    {
        "id": "IBC-002",
        "category": "Insolvency and Bankruptcy Code",
        "sub_category": "Operational Creditor & Pre-existing Dispute",
        "statute": "Insolvency and Bankruptcy Code, 2016",
        "relevant_sections": ["Section 8 IBC", "Section 9 IBC"],
        "question": "What is the effect of a 'pre-existing dispute' raised in reply to a Section 8 demand notice on a Section 9 IBC petition?",
        "ground_truth_context": "Section 9(5)(ii)(d) provides that the Adjudicating Authority shall reject the application if notice of dispute has been received by the operational creditor. Mobilox held that if there is a plausible contention requiring further investigation, the petition must be rejected.",
        "ground_truth_answer": "Under Section 8 & 9 IBC, if the corporate debtor raises a genuine, bona fide 'pre-existing dispute' prior to the receipt of the Section 8 demand notice (e.g. prior emails complaining of sub-standard goods or pending suit), the NCLT **must reject** the Section 9 petition. The IBC cannot be used as a debt recovery tool.",
        "key_statutory_ingredients": ["Pre-existing dispute bars Sec 9", "Mobilox test", "Not a recovery mechanism"],
        "citation_benchmark": "Mobilox Innovations Pvt. Ltd. v. Kirusa Software Pvt. Ltd. (2018) 1 SCC 353",
        "complexity": "Advanced"
    },
    {
        "id": "IBC-003",
        "category": "Insolvency and Bankruptcy Code",
        "sub_category": "Moratorium Scope",
        "statute": "Insolvency and Bankruptcy Code, 2016",
        "relevant_sections": ["Section 14 IBC"],
        "question": "What actions are prohibited under the Moratorium declared under Section 14 of IBC 2016 upon admission of CIRP?",
        "ground_truth_context": "Section 14(1) prohibits: (a) institution of suits or continuation of pending proceedings against the corporate debtor; (b) transferring, encumbering or disposing of corporate debtor's assets; (c) any action to foreclose or enforce security interest; (d) recovery of property by owner/lessor.",
        "ground_truth_answer": "Under Section 14 IBC, the declaration of Moratorium by NCLT prohibits: (1) Instituting or continuing any civil suits, arbitrations, or executions against the Corporate Debtor; (2) Enforcing or recovering any security interest under SARFAESI; (3) Alienating corporate assets; (4) Terminating essential goods/services. However, criminal proceedings against individual directors (e.g. Sec 138) may continue.",
        "key_statutory_ingredients": ["Prohibition of suits and executions", "SARFAESI actions suspended", "Section 14 IBC moratorium", "P. Mohanraj on Sec 138"],
        "citation_benchmark": "P. Mohanraj v. Shah Brothers Ispat Pvt. Ltd. (2021) 6 SCC 258",
        "complexity": "Advanced"
    },
    {
        "id": "CONT-001",
        "category": "Contract Law",
        "sub_category": "Liquidated Damages vs Penalty",
        "statute": "Indian Contract Act, 1872",
        "relevant_sections": ["Section 74"],
        "question": "Can a party enforce the entire pre-estimated liquidated damages stipulated in a contract without proving actual loss under Section 74?",
        "ground_truth_context": "Section 74 provides that the aggrieved party is entitled to receive reasonable compensation not exceeding the amount named. In Kailash Nath, the Supreme Court held that where damage is capable of being proved, proof of actual damage or loss is a condition precedent.",
        "ground_truth_answer": "No. Under Section 74 of the Indian Contract Act (reaffirmed in Kailash Nath Associates), liquidated damages are a ceiling on compensation, not an automatic forfeiture. The claimant must prove actual loss or injury suffered due to breach; only where it is impossible to assess actual loss can a genuine pre-estimate be awarded.",
        "key_statutory_ingredients": ["Section 74 Contract Act", "Proof of actual loss required where possible", "Stipulated sum is a ceiling"],
        "citation_benchmark": "Kailash Nath Associates v. DDA (2015) 4 SCC 136",
        "complexity": "Advanced"
    },
    {
        "id": "CONT-002",
        "category": "Contract Law",
        "sub_category": "Frustration vs Force Majeure",
        "statute": "Indian Contract Act, 1872",
        "relevant_sections": ["Section 32", "Section 56"],
        "question": "What is the difference between contractual Force Majeure under Section 32 and Frustration of Contract under Section 56 of the Indian Contract Act?",
        "ground_truth_context": "In Energy Watchdog, the Supreme Court held that if the contract contains a force majeure clause, it is governed by Section 32 (contingent contracts). Section 56 applies only where an unexpected supervening event occurs outside the contract rendering performance impossible or unlawful.",
        "ground_truth_answer": "Under the Indian Contract Act: (1) **Section 32 (Force Majeure clause)**: Applies when the contract expressly contemplates unforeseen events; the rights and consequences flow from the contract terms; (2) **Section 56 (Frustration)**: Applies when an unforeseen supervening event fundamentally destroys the basis of the contract without any contractual provision, rendering performance legally or physically impossible.",
        "key_statutory_ingredients": ["Section 32 for express clauses", "Section 56 for supervening impossibility", "Energy Watchdog doctrine"],
        "citation_benchmark": "Energy Watchdog v. CERC (2017) 14 SCC 80",
        "complexity": "Advanced"
    },

    # ---------------------------------------------------------
    # PILLAR 8: Consumer Protection & Digital/Data Privacy
    # ---------------------------------------------------------
    {
        "id": "CPA-001",
        "category": "Consumer Protection",
        "sub_category": "Pecuniary Jurisdiction",
        "statute": "Consumer Protection Act, 2019",
        "relevant_sections": ["Section 34", "Section 47", "Section 58"],
        "question": "What are the pecuniary jurisdiction limits of District, State, and National Consumer Commissions under CPA 2019 (as amended in 2021 rules)?",
        "ground_truth_context": "Under the Consumer Protection (Jurisdiction of the District Commission, the State Commission and the National Commission) Rules, 2021: District Commission up to INR 50 Lakhs; State Commission from INR 50 Lakhs to INR 2 Crores; National Commission exceeds INR 2 Crores.",
        "ground_truth_answer": "Under CPA 2019 read with the 2021 Rules: (1) **District Commission**: Consideration paid up to INR 50 Lakhs; (2) **State Commission**: Consideration paid between INR 50 Lakhs and INR 2 Crores; (3) **National Commission (NCDRC)**: Consideration paid exceeding INR 2 Crores.",
        "key_statutory_ingredients": ["District up to 50 Lakhs", "State 50 Lakhs to 2 Crores", "National above 2 Crores", "Based on value of consideration paid"],
        "citation_benchmark": "Neena Aneja v. Jai Prakash Associates Ltd. (2022) 2 SCC 161",
        "complexity": "Basic"
    },
    {
        "id": "CPA-002",
        "category": "Consumer Protection",
        "sub_category": "Product Liability",
        "statute": "Consumer Protection Act, 2019",
        "relevant_sections": ["Section 82", "Section 83", "Section 84", "Section 85"],
        "question": "Who can be held liable in a product liability action under Chapter VI of the Consumer Protection Act, 2019?",
        "ground_truth_context": "Chapter VI CPA 2019 introduces product liability claims against product manufacturers (Sec 84), product service providers (Sec 85), and product sellers (Sec 86) for harm caused by defective products, manufacturing defects, or inadequate warnings.",
        "ground_truth_answer": "Under Chapter VI CPA 2019, a product liability action can be brought against: (1) **Product Manufacturer** (for manufacturing/design defects or deviation from specifications); (2) **Product Service Provider** (for faulty service); (3) **Product Seller** (if they exercised substantial control over design, altered product, or failed to identify manufacturer).",
        "key_statutory_ingredients": ["Manufacturer liability Sec 84", "Service provider liability Sec 85", "Seller liability Sec 86", "Chapter VI CPA 2019"],
        "citation_benchmark": "Statutory Scheme under Chapter VI Consumer Protection Act 2019",
        "complexity": "Intermediate"
    },
    {
        "id": "CYBER-001",
        "category": "Information Technology & Cyber Law",
        "sub_category": "Intermediary Safe Harbor",
        "statute": "Information Technology Act, 2000",
        "relevant_sections": ["Section 79 IT Act"],
        "question": "What are the prerequisites for an internet intermediary to claim Safe Harbor protection under Section 79 of the IT Act?",
        "ground_truth_context": "Section 79 grants immunity to intermediaries for third-party content provided they observe due diligence. In Shreya Singhal, the Supreme Court held that intermediary liability under Section 79(3)(b) arises only upon receipt of 'actual knowledge' through a court order or authorized government notification.",
        "ground_truth_answer": "Under Section 79 IT Act: (1) The intermediary must function purely as a passive conduit without initiating or modifying the transmission; (2) Must observe statutory due diligence under IT Rules 2021; (3) Following *Shreya Singhal*, the intermediary loses safe harbor only if it fails to take down unlawful content after receiving 'actual knowledge' via a **Court order or Government directive**.",
        "key_statutory_ingredients": ["Section 79 IT Act safe harbor", "Due diligence under IT Rules", "Actual knowledge via court order (Shreya Singhal)"],
        "citation_benchmark": "Shreya Singhal v. Union of India (2015) 5 SCC 1",
        "complexity": "Advanced"
    },
    {
        "id": "CYBER-002",
        "category": "Information Technology & Cyber Law",
        "sub_category": "Identity Theft and Impersonation",
        "statute": "Information Technology Act, 2000",
        "relevant_sections": ["Section 66C", "Section 66D IT Act"],
        "question": "What are the penalties for Identity Theft and Cheating by Personation using computer resources under Sections 66C and 66D of the IT Act?",
        "ground_truth_context": "Section 66C punishes fraudulent use of electronic signature, password or unique identification feature with imprisonment up to 3 years and fine up to 1 lakh. Section 66D punishes cheating by personation using computer resource with imprisonment up to 3 years and fine up to 1 lakh.",
        "ground_truth_answer": "Under the IT Act 2000: (1) **Section 66C (Identity Theft)**: Fraudulently using another person's password, digital signature, or biometric ID carries imprisonment up to 3 years and a fine up to INR 1 Lakh; (2) **Section 66D (Cheating by Impersonation)**: Cheating someone by impersonating via computer resource carries imprisonment up to 3 years and a fine up to INR 1 Lakh.",
        "key_statutory_ingredients": ["Section 66C identity theft", "Section 66D cheating by personation", "Up to 3 years imprisonment + 1 lakh fine"],
        "citation_benchmark": "Statutory Offences under Sections 66C and 66D IT Act 2000",
        "complexity": "Basic"
    },
    {
        "id": "DPDP-001",
        "category": "Data Privacy",
        "sub_category": "Data Principal Rights and Fiduciary Duties",
        "statute": "Digital Personal Data Protection Act, 2023",
        "relevant_sections": ["Section 6", "Section 8", "Section 11", "Section 12 DPDP"],
        "question": "What are the statutory rights of a Data Principal under Chapter III of the DPDP Act 2023?",
        "ground_truth_context": "Chapter III of DPDP Act 2023 grants Data Principals: (1) Right to access information about personal data (Sec 11); (2) Right to correction and erasure (Sec 12); (3) Right of grievance redressal (Sec 13); (4) Right to nominate a representative (Sec 14).",
        "ground_truth_answer": "Under Chapter III DPDP Act 2023, a Data Principal has: (1) Right to access a summary of personal data being processed; (2) Right to correction of inaccurate data and completion of incomplete data; (3) Right to erasure of data no longer necessary for purpose; (4) Right to readily available grievance redressal; (5) Right to nominate another individual in event of death/incapacity.",
        "key_statutory_ingredients": ["Right to access summary", "Right to correction and erasure", "Right to nominate", "Chapter III DPDP Act 2023"],
        "citation_benchmark": "Statutory Scheme under Chapter III DPDP Act 2023",
        "complexity": "Intermediate"
    },

    # ---------------------------------------------------------
    # PILLAR 9: Property Law & Real Estate (TPA 1882, RERA 2016)
    # ---------------------------------------------------------
    {
        "id": "TPA-001",
        "category": "Property Law",
        "sub_category": "Doctrine of Lis Pendens",
        "statute": "Transfer of Property Act, 1882",
        "relevant_sections": ["Section 52 TPA"],
        "question": "What is the Doctrine of Lis Pendens under Section 52 of the Transfer of Property Act, 1882?",
        "ground_truth_context": "Section 52 provides that during the pendency of any suit or proceeding in which any right to immovable property is directly and specifically in question, the property cannot be transferred or dealt with by any party so as to affect the rights of any other party under any decree or order.",
        "ground_truth_answer": "Under Section 52 TPA, the Doctrine of Lis Pendens dictates that during the pendency of a contentious suit where rights in immovable property are directly in issue, no party can transfer or alienate the property so as to defeat the opponent's rights. The transferee pendente lite is bound by the ultimate court decree, even without being a party.",
        "key_statutory_ingredients": ["Pending contentious litigation", "Property right directly in issue", "Transferee bound by final decree", "Section 52 TPA"],
        "citation_benchmark": "Gouri Dutt Sharma v. Sukur Mohammed AIR 1948 PC 147",
        "complexity": "Intermediate"
    },
    {
        "id": "TPA-002",
        "category": "Property Law",
        "sub_category": "Gift of Immovable Property",
        "statute": "Transfer of Property Act, 1882",
        "relevant_sections": ["Section 122", "Section 123 TPA"],
        "question": "What are the essential statutory requirements for a valid Gift of immovable property under Section 123 TPA?",
        "ground_truth_context": "Section 122 defines gift as the transfer of certain existing movable or immovable property made voluntarily and without consideration. Section 123 mandates that for immovable property, the transfer must be effected by a registered instrument signed by or on behalf of the donor and attested by at least two witnesses.",
        "ground_truth_answer": "Under Sections 122 and 123 TPA: (1) Voluntary transfer without consideration; (2) Acceptance by or on behalf of the donee during the lifetime of the donor; (3) For immovable property, it **must be effected by a registered instrument signed by the donor and attested by at least two witnesses**.",
        "key_statutory_ingredients": ["Voluntary without consideration", "Acceptance during donor's lifetime", "Registered instrument with 2 attesting witnesses", "Section 123 TPA"],
        "citation_benchmark": "K. Balakrishnan v. K. Kamalam (2004) 1 SCC 581",
        "complexity": "Basic"
    },
    {
        "id": "TPA-003",
        "category": "Property Law",
        "sub_category": "Fraudulent Transfer",
        "statute": "Transfer of Property Act, 1882",
        "relevant_sections": ["Section 53 TPA"],
        "question": "Can creditors set aside a transfer of immovable property made by a debtor to defeat their recovery under Section 53 TPA?",
        "ground_truth_context": "Section 53(1) TPA provides that every transfer of immovable property made with intent to defeat or delay the creditors of the transferor shall be voidable at the option of any creditor so defeated or delayed, except in case of a transferee in good faith and for consideration.",
        "ground_truth_answer": "Yes. Under Section 53 TPA, any transfer of immovable property made with intent to defeat or delay creditors is voidable at the option of the affected creditors. However, the rule does not impair the rights of a bona fide purchaser for valuable consideration without notice of fraudulent intent.",
        "key_statutory_ingredients": ["Intent to defeat or delay creditors", "Voidable at creditor's option", "Bona fide purchaser exception", "Section 53 TPA"],
        "citation_benchmark": "Abdul Shukoor Attar v. Golden Paper Stores AIR 1963 SC 1150",
        "complexity": "Intermediate"
    },
    {
        "id": "RERA-001",
        "category": "Real Estate Regulation",
        "sub_category": "Homebuyer Refund Rights",
        "statute": "Real Estate (Regulation and Development) Act, 2016",
        "relevant_sections": ["Section 18 RERA"],
        "question": "What remedies does a homebuyer have under Section 18 of RERA 2016 if the builder fails to deliver possession on the promised date?",
        "ground_truth_context": "Section 18(1) RERA provides that if the promoter fails to give possession in accordance with the agreement for sale, he shall be liable on demand to the allottee: (a) to return the entire amount received with prescribed interest; or (b) if allottee does not withdraw, pay interest for every month of delay.",
        "ground_truth_answer": "Under Section 18 RERA 2016, if a promoter delays possession: (1) The homebuyer has an absolute right to withdraw from the project and demand full refund of the amount paid with interest at prescribed SBI MCLR + 2% rate, plus compensation; OR (2) If they choose to stay in the project, they are entitled to monthly delay interest until possession.",
        "key_statutory_ingredients": ["Absolute right to refund with interest", "Monthly interest for delay if staying", "Section 18 RERA", "Imperia Structures ruling"],
        "citation_benchmark": "Imperia Structures Ltd. v. Anil Patni (2020) 10 SCC 783",
        "complexity": "Intermediate"
    },

    # ---------------------------------------------------------
    # PILLAR 10: Family Law & Matrimonial Relief
    # ---------------------------------------------------------
    {
        "id": "FAM-001",
        "category": "Family & Matrimonial Law",
        "sub_category": "Mutual Consent Divorce Waiver",
        "statute": "Hindu Marriage Act, 1955",
        "relevant_sections": ["Section 13B(1)", "Section 13B(2) HMA"],
        "question": "Can the 6-month statutory waiting period (cooling-off period) under Section 13B(2) of the Hindu Marriage Act be waived by the Court?",
        "ground_truth_context": "Section 13B(2) provides a waiting period of six to eighteen months between first and second motions. In Amardeep Singh v. Harveen Kaur, the Supreme Court held that the 6-month period is directory and can be waived by the family court if all efforts of mediation failed and parties have settled claims.",
        "ground_truth_answer": "Yes. In *Amardeep Singh v. Harveen Kaur*, the Supreme Court held that the 6-month waiting period under Section 13B(2) HMA is directory, not mandatory. The Family Court can waive the cooling-off period if: (1) The 18-month statutory separation has already passed; (2) Mediation has failed; (3) All alimony, custody, and property disputes are amicably resolved.",
        "key_statutory_ingredients": ["Section 13B(2) directory, not mandatory", "Family Court power to waive 6 months", "Settlement of all claims"],
        "citation_benchmark": "Amardeep Singh v. Harveen Kaur (2017) 8 SCC 746",
        "complexity": "Intermediate"
    },
    {
        "id": "FAM-002",
        "category": "Family & Matrimonial Law",
        "sub_category": "Domestic Violence Residence Orders",
        "statute": "Protection of Women from Domestic Violence Act, 2005",
        "relevant_sections": ["Section 17", "Section 19 PWDVA"],
        "question": "Does an aggrieved woman have a right of residence in a shared household under Section 17 & 19 of the Domestic Violence Act if the property belongs to her in-laws?",
        "ground_truth_context": "In Satish Chander Ahuja, the Supreme Court overruled S.R. Batra and held that 'shared household' under Section 2(s) and Section 17 is not restricted to property owned by the husband alone; it includes property where the aggrieved person lived in a domestic relationship, even if owned by in-laws.",
        "ground_truth_answer": "Yes. Overruling the restrictive *S.R. Batra* precedent, the Supreme Court in *Satish Chander Ahuja v. Sneha Ahuja* held that under Section 17 and 19 PWDVA, an aggrieved woman has a statutory right to reside in the shared household even if the premises belong exclusively to her father-in-law or mother-in-law, provided she lived there in a domestic relationship.",
        "key_statutory_ingredients": ["Section 17 right to reside", "Section 19 residence orders", "Shared household includes in-laws' property", "Satish Chander Ahuja 3-judge bench"],
        "citation_benchmark": "Satish Chander Ahuja v. Sneha Ahuja (2021) 1 SCC 414",
        "complexity": "Advanced"
    }
]

def main():
    target_dir = Path(r"d:\Study\LegalDrishti AI\evaluation")
    target_dir.mkdir(parents=True, exist_ok=True)

    json_path = target_dir / "golden_dataset.json"
    csv_path = target_dir / "golden_dataset.csv"

    # Write JSON
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(DATASET_ITEMS, f, indent=2, ensure_ascii=False)

    # Write CSV
    fieldnames = [
        "id", "category", "sub_category", "statute", "relevant_sections",
        "question", "ground_truth_context", "ground_truth_answer",
        "key_statutory_ingredients", "citation_benchmark", "complexity"
    ]
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for item in DATASET_ITEMS:
            row = item.copy()
            row["relevant_sections"] = "; ".join(row["relevant_sections"])
            row["key_statutory_ingredients"] = "; ".join(row["key_statutory_ingredients"])
            writer.writerow(row)

    print(f"Generated {len(DATASET_ITEMS)} golden evaluation scenarios successfully in {target_dir}!")

if __name__ == "__main__":
    main()
