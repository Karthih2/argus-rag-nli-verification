# Golden Set (NASA)

150 claims + 60 questions (12 unanswerable), handwritten, labelled by both teammates.

## Structure

- `questions.jsonl`: 60 questions with expected answers, content types, and gold chunk IDs
- `claims.jsonl`: 150 claims with gold labels (SUPPORTED/CONTRADICTED/UNVERIFIED)

## Content type distribution (claims)

| Type | Count |
|------|-------|
| Text | 60 |
| Tables | 30 |
| Charts | 15 |
| KPIs/numbers | 20 |
| Quotes | 15 |
| Multi-hop | 10 |

## Notes

- 15 questions are follow-ups inside 5 short conversations (tests rewrite step)
- 20 questions target tables or charts, 8 target photos/diagrams
- Mutations follow FEVER: negation, entity swap, number change, generalisation
- Cohen's kappa reported for inter-annotator agreement
