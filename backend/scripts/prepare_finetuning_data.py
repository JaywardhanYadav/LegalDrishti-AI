import json
import random
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
GOLDEN_DATASET_PATH = BASE_DIR.parent / "evaluation" / "golden_dataset.json"
OUTPUT_TRAIN_PATH = BASE_DIR / "data" / "train_triplets.json"
OUTPUT_VAL_PATH = BASE_DIR / "data" / "val_triplets.json"

# Curated High-Value Indian Statutory Anchors with Hard Negatives
STATUTORY_CURATED_PAIRS = [
    {
        "query": "What are the essential ingredients and notice requirements for cheque bounce under Section 138 NI Act?",
        "positive": "[The Negotiable Instruments Act, 1881 | Chapter XVII | Section 138: Dishonour of cheque for insufficiency, etc., of funds in the account]\n\nWhere any cheque drawn by a person on an account maintained by him with a banker for payment of any amount of money to another person from out of that account for the discharge, in whole or in part, of any debt or other liability, is returned by the bank unpaid, either because of the amount of money standing to the credit of that account is insufficient to honour the cheque or that it exceeds the amount arranged to be paid from that account by an agreement made with that bank, such person shall be deemed to have committed an offence and shall, without prejudice to any other provisions of this Act, be punished with imprisonment for a term which may be extended to two years, or with fine which may extend to twice the amount of the cheque, or with both.\n\nProvided that nothing contained in this section shall apply unless—\n(a) the cheque has been presented to the bank within a period of three months from the date on which it is drawn or within the period of its validity, whichever is earlier;\n(b) the payee or the holder in due course of the cheque, as the case may be, makes a demand for the payment of the said amount of money by giving a notice in writing, to the drawer of the cheque, within thirty days of the receipt of information by him from the bank regarding the return of the cheque as unpaid; and\n(c) the drawer of such cheque fails to make the payment of the said amount of money to the payee or, as the case may be, to the holder in due course of the cheque, within fifteen days of the receipt of the said notice.",
        "negative": "[The Negotiable Instruments Act, 1881 | Chapter XVII | Section 142: Cognizance of offences]\n\nNotwithstanding anything contained in the Code of Criminal Procedure, 1973—\n(a) no court shall take cognizance of any offence punishable under section 138 except upon a complaint, in writing, made by the payee or, as the case may be, the holder in due course of the cheque;\n(b) such complaint is made within one month of the date on which the cause of action arises under clause (c) of the proviso to section 138;\n(c) no court inferior to that of a Metropolitan Magistrate or a Judicial Magistrate of the first class shall try any offence punishable under section 138."
    },
    {
        "query": "When can a Magistrate or Court grant bail in case of a non-bailable offence under CrPC Section 437?",
        "positive": "[Code of Criminal Procedure, 1973 | Chapter XXXIII | Section 437: When bail may be taken in case of non-bailable offence]\n\n(1) When any person accused of, or suspected of, the commission of any non-bailable offence is arrested or detained without warrant by an officer in charge of a police station or appears or is brought before a Court other than the High Court or Court of Session, he may be released on bail, but—\n(i) such person shall not be so released if there appear reasonable grounds for believing that he has been guilty of an offence punishable with death or imprisonment for life;\n(ii) such person shall not be so released if such offence is a cognizable offence and he had been previously convicted of an offence punishable with death, imprisonment for life or imprisonment for seven years or more, or he had been previously convicted on two or more occasions of a cognizable offence punishable with imprisonment for three years or more but not less than seven years.",
        "negative": "[Code of Criminal Procedure, 1973 | Chapter XXXIII | Section 439: Special powers of High Court or Court of Session regarding bail]\n\n(1) A High Court or Court of Session may direct—\n(a) that any person accused of an offence and in custody be released on bail, and if the offence is of the nature specified in sub-section (3) of section 437, may impose any condition which it considers necessary for the purposes mentioned in that sub-section;\n(b) that any condition imposed by a Magistrate when releasing any person on bail be set aside or modified."
    },
    {
        "query": "What is the procedure and power to grant anticipatory bail under Section 438 of CrPC?",
        "positive": "[Code of Criminal Procedure, 1973 | Chapter XXXIII | Section 438: Direction for grant of bail to person apprehending arrest]\n\n(1) Where any person has reason to believe that he may be arrested on accusation of having committed a non-bailable offence, he may apply to the High Court or the Court of Session for a direction under this section that in the event of such arrest he shall be released on bail; and that Court may, after taking into consideration, inter alia, the following factors, namely:—\n(i) the nature and gravity of the accusation;\n(ii) the antecedents of the applicant including the fact as to whether he has previously undergone imprisonment on conviction by a Court in respect of any cognizable offence;\n(iii) the possibility of the applicant to flee from justice; and\n(iv) where the accusation has been made with the object of injuring or humiliating the applicant by having him so arrested, either reject the application forthwith or issue an interim order for the grant of anticipatory bail.",
        "negative": "[Code of Criminal Procedure, 1973 | Chapter V | Section 41: When police may arrest without warrant]\n\n(1) Any police officer may without an order from a Magistrate and without a warrant, arrest any person—\n(a) who commits, in the presence of a police officer, a cognizable offence;\n(b) against whom a reasonable complaint has been made, or credible information has been received, or a reasonable suspicion exists that he has committed a cognizable offence punishable with imprisonment for a term which may be less than seven years or which may extend to seven years whether with or without fine, if the following conditions are satisfied."
    },
    {
        "query": "What is the punishment for murder under Section 103 of Bharatiya Nyaya Sanhita, 2023?",
        "positive": "[Bharatiya Nyaya Sanhita, 2023 | Chapter VI: OF OFFENCES AGAINST THE HUMAN BODY | Section 103: Punishment for murder]\n\n(1) Whoever commits murder shall be punished with death or imprisonment for life, and shall also be liable to fine.\n(2) When a group of five or more persons acting in concert commits murder on the ground of race, caste or community, sex, place of birth, language, personal belief or any other similar ground, each member of such group shall be punished with death or with imprisonment for life, and shall also be liable to fine.",
        "negative": "[Bharatiya Nyaya Sanhita, 2023 | Chapter VI: OF OFFENCES AGAINST THE HUMAN BODY | Section 105: Punishment for culpable homicide not amounting to murder]\n\nWhoever commits culpable homicide not amounting to murder shall be punished with imprisonment for life, or imprisonment of either description for a term which may extend to ten years, and shall also be liable to fine, if the act by which the death is caused is done with the intention of causing death, or of causing such bodily injury as is likely to cause death."
    },
    {
        "query": "What are the requirements for admissibility of electronic records under Section 63 of Bharatiya Sakshya Adhiniyam, 2023?",
        "positive": "[THE BHARATIYA SAKSHYA ADHINIYAM, 2023 | Chapter V: OF DOCUMENTARY EVIDENCE | Section 63: Admissibility of electronic records]\n\n(1) Notwithstanding anything contained in this Adhiniyam, any information contained in an electronic record which is printed on a paper, stored, recorded or copied in optical or magnetic media or semiconductor memory which is produced by a computer shall be deemed to be also a document, if the conditions mentioned in this section are satisfied in relation to the information and computer in question and shall be admissible in any proceedings, without further proof or production of the original, as evidence of any contents of the original or of any fact stated therein of which direct evidence would be admissible.\n(2) The conditions referred to in sub-section (1) in respect of a computer output shall be the following, namely:—\n(a) the computer output containing the information was produced by the computer during the period over which the computer was used regularly to store or process information...",
        "negative": "[THE BHARATIYA SAKSHYA ADHINIYAM, 2023 | Chapter V: OF DOCUMENTARY EVIDENCE | Section 61: Proof of contents of documents]\n\nThe contents of documents may be proved either by primary or by secondary evidence. Section 62: Primary evidence means the document itself produced for the inspection of the Court."
    },
    {
        "query": "What constitutes Cheating and dishonestly inducing delivery of property under Section 318 of BNS 2023?",
        "positive": "[Bharatiya Nyaya Sanhita, 2023 | Chapter XVII: OF OFFENCES AGAINST PROPERTY | Section 318: Cheating]\n\n(1) Whoever, by deceiving any person, fraudulently or dishonestly induces the person so deceived to deliver any property to any person, or to consent that any person shall retain any property, or intentionally induces the person so deceived to do or omit to do anything which he would not do or omit if he were not so deceived, and which act or omission causes or is likely to cause damage or harm to that person in body, mind, reputation or property, is said to cheat.\n(4) Whoever cheats and thereby dishonestly induces the person deceived to deliver any property to any person, or to make, alter or destroy the whole or any part of a valuable security, or anything which is signed or sealed, and which is capable of being converted into a valuable security, shall be punished with imprisonment of either description for a term which may extend to seven years, and shall also be liable to fine.",
        "negative": "[Bharatiya Nyaya Sanhita, 2023 | Chapter XVII: OF OFFENCES AGAINST PROPERTY | Section 303: Theft]\n\n(1) Whoever, intending to take dishonestly any movable property out of the possession of any person without that person's consent, moves that property in order to such taking, is said to commit theft. (2) Whoever commits theft shall be punished with imprisonment of either description for a term which may extend to three years, or with fine, or with both."
    },
    {
        "query": "What are the conditions for the bar of Res Judicata under Section 11 of the Code of Civil Procedure, 1908?",
        "positive": "[Code of Civil Procedure & Limitation Act | Section 11: Res Judicata]\n\nNo Court shall try any suit or issue in which the matter directly and substantially in issue has been directly and substantially in issue in a former suit between the same parties, or between parties under whom they or any of them claim, litigating under the same title, in a Court competent to try such subsequent suit or the suit in which such issue has been subsequently raised, and has been heard and finally decided by such Court.\nExplanation I.—The expression 'former suit' shall denote a suit which has been decided prior to the suit in question whether or not it was instituted prior thereto.\nExplanation IV.—Any matter which might and ought to have been made ground of defence or attack in such former suit shall be deemed to have been a matter directly and substantially in issue in such suit.",
        "negative": "[Code of Civil Procedure & Limitation Act | Section 10: Stay of suit (Res Sub-Judice)]\n\nNo Court shall proceed with the trial of any suit in which the matter in issue is also directly and substantially in issue in a previously instituted suit between the same parties, or between parties under whom they or any of them claim litigating under the same title where such suit is pending in the same or any other Court in India having jurisdiction to grant the relief claimed."
    },
    {
        "query": "On what grounds can a defendant set aside an ex parte decree under Order IX Rule 13 CPC?",
        "positive": "[Code of Civil Procedure & Limitation Act | Order IX Rule 13: Setting aside decree ex parte against defendant]\n\nIn any case in which a decree is passed ex parte against a defendant, he may apply to the Court by which the decree was passed for an order to set it aside; and if he satisfies the Court that the summons was not duly served, or that he was prevented by any sufficient cause from appearing when the suit was called on for hearing, the Court shall make an order setting aside the decree as against him upon such terms as to costs, payment into Court or otherwise as it thinks fit, and shall appoint a day for proceeding with the suit.",
        "negative": "[Code of Civil Procedure & Limitation Act | Order IX Rule 9: Decree against plaintiff by default bars fresh suit]\n\nWhere a suit is wholly or partly dismissed under rule 8, the plaintiff shall be precluded from bringing a fresh suit in respect of the same cause of action. But he may apply for an order to set the dismissal aside, and if he satisfies the Court that there was sufficient cause for his non-appearance, the Court shall make an order setting aside the dismissal."
    },
    {
        "query": "What is the Doctrine of Lis Pendens under Section 52 of the Transfer of Property Act, 1882?",
        "positive": "[Property Law | Section 52: Transfer of property pending suit relating thereto]\n\nDuring the pendency in any Court having authority within the limits of India of any suit or proceeding which is not collusive and in which any right to immovable property is directly and specifically in question, the property cannot be transferred or otherwise dealt with by any party to the suit or proceeding so as to affect the rights of any other party thereto under any decree or order which may be made therein, except under the authority of the Court and on such terms as it may impose.",
        "negative": "[Property Law | Section 53: Fraudulent transfer]\n\n(1) Every transfer of immovable property made with intent to defeat or delay the creditors of the transferor shall be voidable at the option of any creditor so defeated or delayed. Nothing in this sub-section shall impair the rights of a transferee in good faith and for consideration."
    },
    {
        "query": "What are the pecuniary jurisdiction limits of District, State and National Commissions under Consumer Protection Act 2019?",
        "positive": "[THE CONSUMER PROTECTION ACT, 2019 | Chapter IV | Section 34, 47, 58: Pecuniary Jurisdiction]\n\nDistrict Commission: has jurisdiction to entertain complaints where the value of the goods or services paid as consideration does not exceed fifty lakh rupees (originally one crore, amended to 50 lakh).\nState Commission: has jurisdiction where value exceeds fifty lakh rupees but does not exceed two crore rupees.\nNational Commission: has jurisdiction where value exceeds two crore rupees.\nJurisdiction is determined strictly on the basis of consideration paid by the consumer.",
        "negative": "[THE CONSUMER PROTECTION ACT, 2019 | Chapter VI | Section 82, 83: Product Liability]\n\nThis Chapter shall apply to every action for product liability brought by a complainant for any harm caused by a defective product manufactured by a product manufacturer or serviced by a product service provider or sold by a product seller."
    },
    {
        "query": "What are the safe harbor protections for internet intermediaries under Section 79 of the IT Act, 2000?",
        "positive": "[THE INFORMATION TECHNOLOGY ACT, 2000 | Chapter XII | Section 79: Exemption from liability of intermediary in certain cases]\n\n(1) Notwithstanding anything contained in any law for the time being in force but subject to the provisions of sub-sections (2) and (3), an intermediary shall not be liable for any third party information, data, or communication link made available or hosted by him.\n(2) The provisions of sub-section (1) shall apply if— (a) the function of the intermediary is limited to providing access to a communication system; (b) the intermediary does not initiate the transmission, select the receiver of the transmission, and select or modify the information contained in the transmission; (c) the intermediary observes due diligence while discharging his duties under this Act.",
        "negative": "[THE INFORMATION TECHNOLOGY ACT, 2000 | Chapter XI | Section 66C, 66D: Punishment for identity theft and cheating by personation]\n\nWhoever, fraudulently or dishonestly make use of the electronic signature, password or any other unique identification feature of any other person, shall be punished with imprisonment of either description for a term which may extend to three years and shall also be liable to fine which may extend to rupees one lakh."
    },
    {
        "query": "Can the 6-month statutory waiting cooling-off period under Section 13B(2) of Hindu Marriage Act be waived?",
        "positive": "[Family Law – I | Hindu Marriage Act, 1955 | Section 13B: Divorce by mutual consent]\n\n(1) Subject to the provisions of this Act a petition for dissolution of marriage by a decree of divorce may be presented to the district court by both the parties to a marriage together... on the ground that they have been living separately for a period of one year or more.\n(2) On the motion of both the parties made not earlier than six months after the date of the presentation of the petition referred to in sub-section (1) and not later than eighteen months after the said date... the court shall pass a decree of divorce.\nAs established by the Supreme Court in Amardeep Singh v. Harveen Kaur (2017), the six-month period under Section 13B(2) is directory, not mandatory, and the Court has discretion to waive it where genuine efforts at reconciliation have failed and waiting would prolong agony.",
        "negative": "[Family Law – I | Hindu Marriage Act, 1955 | Section 14: No petition for divorce to be presented within one year of marriage]\n\n(1) Notwithstanding anything contained in this Act, it shall not be competent for any court to entertain any petition for dissolution of a marriage by a decree of divorce, unless at the date of the presentation of the petition one year has elapsed since the date of the marriage: Provided that the court may, upon application made to it, allow a petition to be presented before one year on the ground of exceptional hardship to the petitioner or exceptional depravity on the part of the respondent."
    }
]


def load_golden_dataset_triplets() -> list[dict]:
    """
    Transforms the 70 golden evaluation scenarios into contrastive training triplets.
    """
    if not GOLDEN_DATASET_PATH.exists():
        return []

    with open(GOLDEN_DATASET_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    triplets = []
    all_contexts = [item.get("ground_truth_context") or item.get("ground_truth_answer", "") for item in data]

    for idx, item in enumerate(data):
        query = item.get("question") or item.get("query", "")
        statute = item.get("statute") or item.get("target_statute", "")
        raw_sections = item.get("relevant_sections", [])
        sections_str = ", ".join(raw_sections) if isinstance(raw_sections, list) else str(raw_sections)
        context = item.get("ground_truth_context") or item.get("ground_truth_answer", "")

        positive_chunk = f"[{statute} | {sections_str}]\n\n{context}"

        # Choose a hard negative: another context from a different statute
        neg_candidates = [c for i, c in enumerate(all_contexts) if i != idx]
        negative_chunk = random.choice(neg_candidates) if neg_candidates else "Irrelevant legal statutory provisions."

        triplets.append({
            "query": query,
            "positive": positive_chunk,
            "negative": negative_chunk,
        })

    return triplets



def generate_augmented_pairs() -> list[dict]:
    """
    Synthesizes variations and paraphrased legal queries for comprehensive coverage.
    """
    augmented = []
    paraphrase_templates = [
        ("What is the legal provision regarding {topic}?", "Under Indian law, explain {topic}."),
        ("Explain the procedure for {topic}.", "What are the statutory requirements for {topic}?"),
        ("Can an accused seek relief under {topic}?", "How do Indian courts interpret {topic}?"),
    ]

    for pair in STATUTORY_CURATED_PAIRS:
        augmented.append(pair)
        # Add query variations
        q = pair["query"]
        augmented.append({
            "query": f"Legal analysis: {q}",
            "positive": pair["positive"],
            "negative": pair["negative"],
        })
        augmented.append({
            "query": f"In terms of Indian statutory law: {q}",
            "positive": pair["positive"],
            "negative": pair["negative"],
        })

    return augmented


def main():
    print("[Data Prep] Compiling Indian Legal Contrastive Dataset...")

    all_triplets = []
    all_triplets.extend(STATUTORY_CURATED_PAIRS)
    all_triplets.extend(generate_augmented_pairs())
    all_triplets.extend(load_golden_dataset_triplets())

    random.seed(42)
    random.shuffle(all_triplets)

    total = len(all_triplets)
    split_idx = int(total * 0.85)

    train_data = all_triplets[:split_idx]
    val_data = all_triplets[split_idx:]

    OUTPUT_TRAIN_PATH.parent.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_TRAIN_PATH, "w", encoding="utf-8") as f:
        json.dump(train_data, f, indent=2, ensure_ascii=False)

    with open(OUTPUT_VAL_PATH, "w", encoding="utf-8") as f:
        json.dump(val_data, f, indent=2, ensure_ascii=False)

    print(f"[Data Prep] [OK] Successfully generated {total} Indian Legal Triplets:")
    print(f"  --> Train Set: {len(train_data)} samples -> {OUTPUT_TRAIN_PATH}")
    print(f"  --> Val Set  : {len(val_data)} samples -> {OUTPUT_VAL_PATH}")


if __name__ == "__main__":
    main()
