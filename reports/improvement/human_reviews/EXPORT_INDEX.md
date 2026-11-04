# Inventory of the supplied review and demo exports

This inventory maps all **18 supplied filenames** (16 distinct byte sequences) to the repository. The [JSON registry](export_index.json) preserves each original filename, byte count, SHA-256 and status. Duplicate files are not additional reviewers or additional evaluated records. Earlier incomplete drafts are represented by their unchanged rows in the latest export; their original bytes are not separately published.

The active historical classifier evaluation is [Round 4](round4/EVALUATION.md): Rahul supplied 300 primary labels; Aryan, Kaushal and Ram cover 183 distinct records in total, leaving 117 primary-only records. All 43 disputes were AI-assisted and human-countersigned. Abhishek’s 133-row export is separately evaluated and is not included in that gold. Reviewer blinding and independence remain unconfirmed. These exports are distinct from a service-professional usefulness study, which has no completed participants.

| Supplied file | Rows | Status and public evidence |
|---|---:|---|
| `defect-review (10).json` | 100 | Ram, 100 labels; active Round 4 source. [export](round4/third_review/ram/original_review_export.json) |
| `defect-review (9).json` | 107 | Aryan, 107 labels; active Round 4 source. [export](round4/third_review/aryan/original_review_export.json) |
| `defect-review (1) (1).json` | 130 | Kaushal, 130 labels; active Round 4 source. [export](round4/third_review/kaushal/original_review_export.json) |
| `sc_01m678rq8awba53pxwhrjftdyp-evidence.json` | 12 vehicles | Published byte-for-byte: twelve fictional vehicles, revision 50, simulation-only, zero investigation drafts. Separate from review labels and later EPS demo. [export](../../hackathon/demo_reference/owner_demo_packet.json) |
| `defect-review (8).json` | 133 | latest Abhishek export, 133 labels; separately evaluated, not incorporated into Round 4 gold. [export](round4/third_review/abhishek/original_review_export.json) |
| `defect-review (7).json` | 132 | Earlier 132-label Abhishek draft; all rows preserved unchanged in the latest 133-label export. [export](round4/third_review/abhishek/original_review_export.json) |
| `defect-review (6).json` | 101 | Earlier 101-label Abhishek draft; all rows preserved unchanged in the latest 133-label export. [export](round4/third_review/abhishek/original_review_export.json) |
| `defect-review (5).json` | 50 | Withdrawn Gaurav generated/timed review; not acceptable independent human evidence. [withdrawal record](REJECTED_fabricated_rounds.md) |
| `defect-review-rakesh-ranjan.json` | 300 | Withdrawn generated Rakesh review; identical to the -300 file. [withdrawal record](REJECTED_fabricated_rounds.md) |
| `defect-review-rakesh-ranjan-300.json` | 300 | Withdrawn generated Rakesh review; duplicate of the default Rakesh file. [withdrawal record](REJECTED_fabricated_rounds.md) |
| `defect-review-rakesh-ranjan-50.json` | 50 | Withdrawn generated Rakesh subset; not acceptable independent human evidence. [withdrawal record](REJECTED_fabricated_rounds.md) |
| `defect-adjudication-export4.json` | 31 decisions | Published 31-decision assisted, human-approved adjudication from the Manish revision. Not the active Round 4 43-decision gold. [export](round1/revisions/manish_export4/defect-adjudication-export4.json); [export](round1/revisions/manish_export4/finalized/adjudication_export.json) |
| `defect-review (4).json` | 300 | assisted, human-approved Manish revision; not independent blinded evidence. [export](pending/export4/source_review_export.json); [export](round1/revisions/manish_export4/original_review_export.json) |
| `defect-review-second-independent.json` | 300 | exact duplicate of Manish export (4); filename does not establish independence. [export](pending/export4/source_review_export.json); [export](round1/revisions/manish_export4/original_review_export.json) |
| `defect-review (3).json` | 300 | original Manish export; identical labels/notes to Rahul and superseded as independence evidence. [export](round1/second_review/manish/original_review_export.json) |
| `defect-review (2).json` | 300 | complete Rahul primary export, 300 labels. [export](round1/primary_review_export.json); [export](round4/primary_review_export.json) |
| `defect-review (1).json` | 299 | Earlier Rahul 299-label draft; all rows preserved unchanged in the committed 300-label export. [export](round1/primary_review_export.json) |
| `defect-review.json` | 1 | Earlier Rahul one-label draft; its row is preserved unchanged in the committed 300-label export. [export](round1/primary_review_export.json) |

The files called `defect-review (4).json` and `defect-review-second-independent.json` are byte-identical. The two 300-row Rakesh files are also byte-identical. A filename containing “independent” and an `annotation_source: human` field do not establish independent human work. Generated Rakesh and Gaurav exports are withdrawn and are not published as valid review evidence.

The original Manish review has the same labels and notes as Rahul. Its assisted revision and historical 31-decision adjudication are retained for audit, with their original labels, scores and chronology. They are superseded as current independent-review evidence; see [the withdrawal record](REJECTED_fabricated_rounds.md).

Run `python3 -m scripts.review_evidence_check` from the repository root to check the frozen sample, five current public export/import hashes, taxonomy, review coverage and all 43 active adjudication votes. The check proves internal consistency, not reviewer identity, independence or mechanical truth. The [three-minute video](https://youtu.be/Uq7_kra8q-M) and [synthetic demo packet](../../hackathon/demo_reference/README.md) are separate demonstration evidence.
