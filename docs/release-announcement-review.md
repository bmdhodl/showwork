# Show Work release announcements: existing-path review

Prepared October 3, 2026 for [#105](https://github.com/bmdhodl/showwork/issues/105).
No campaign was sent, production cohort queried, credential loaded, preference
model changed or sender activated during this review.

Current bmdpat main `2ed6d266a287a2c63a6d38ec3e0cf6f6af917f87` already contains
`PRODUCT_RELEASE_CONSENT_VERSION = 2026-09-product-releases-v1`, a disclosure
explicitly naming Show Work, `scripts/send_product_release.py`, the existing
newsletter send service and `subscriber_email_deliveries`. General newsletter
consent remains a different version. Show Work's source allowlist contains only
`product-releases`; AgentGuard's older acquisition sources are not reused for it.
No new preference schema is needed to propose stricter use of these existing
fields. Production adoption still belongs to bmdpat's approval lane.

Originals:
[release identities](https://github.com/bmdhodl/bmdpat/blob/2ed6d266a287a2c63a6d38ec3e0cf6f6af917f87/src/lib/product-releases.ts),
[sender](https://github.com/bmdhodl/bmdpat/blob/2ed6d266a287a2c63a6d38ec3e0cf6f6af917f87/scripts/send_product_release.py),
[send route](https://github.com/bmdhodl/bmdpat/blob/2ed6d266a287a2c63a6d38ec3e0cf6f6af917f87/src/app/api/newsletter/send/route.ts),
[delivery ledger](https://github.com/bmdhodl/bmdpat/blob/2ed6d266a287a2c63a6d38ec3e0cf6f6af917f87/src/lib/subscriber-email-delivery.ts).

## Existing behavior and gaps

| Requirement | Source observation | Required completion proof |
| --- | --- | --- |
| Published stable release | Sender rejects draft/prerelease/missing publication, unsafe tag and mismatched notes URL | Exact public install smoke for the actual announced wheel |
| Matching package | Sender requires matching PyPI version, nonempty file list and no yanked artifact | Availability is not clean-install behavior; link the release packet before activation |
| Explicit Show Work consent | New disclosure names Show Work; route filters active, unsubscribed-null rows by allowed source | Query does not also require the explicit product-release consent version |
| Retry deduplication | Canonical product/version campaign key; recipient/message-kind/campaign hash; existing claim RPC and completed-row handling | Duplicate webhook and partial-delivery recovery against the real route |
| Send-time consent | Route selects active rows before its loop | Delivery claim does not reread subscriber consent; release `beforeSend` currently delays only, so revocation during the loop needs a tested recheck |
| Complaint / suppression | Route checks the existing pause control; delivery rows expose complained/suppressed/reconciliation states | Verify revoked consent and suppression before the provider call, not only at cohort selection |
| Actual delivery | Sender reports accepted counts and fails incomplete service responses | Provider acceptance is not delivery; owner inbox and provider delivery events remain required |

These gaps are source-reviewed, not a reproduced production incident. No existing
recipient is asserted to have received an unauthorized message. No subscriber
address or private execution content is included in this packet.

Nine existing offline Python sender tests passed from the pinned source with
no credentials or network calls. They cover stable-public identity, package
mismatch/yanking, pinned upgrade and campaign key, missing key, redirect handling
and incomplete-send handling. They do not exercise cohort selection, consent
revocation, actual provider delivery, the rendered email or the database RPC.
Raw output: [offline sender tests](reports/roadmap-readout-20261003/notification-offline-tests.txt).

## Proposed acceptance packet for the bmdpat owner lane

Use the existing consent version and source fields together for Show Work.
Immediately before dispatch, reread active/unsubscribed/suppression/complaint
state and the applicable explicit consent. If any required state cannot be read,
send nothing. Keep the existing delivery ledger and one product/version/recipient
key. A resumed attempt reuses the same key and reconciles unknown provider outcomes;
it must not rebuild another message or mark an accepted request delivered.

| Offline fixture | Required result |
| --- | --- |
| Empty eligible cohort | Zero recipients and zero provider calls |
| General newsletter consent plus product-looking source | Ineligible without explicit product-release consent |
| Explicit authorized product-release cohort | Eligible dummy IDs only; no actual addresses in receipts |
| Duplicate release webhook | One delivery identity; completed rows are not resent |
| Consent revoked after selection | Zero calls for that row after the send-time recheck |
| Complaint pause or suppression | No dispatch |
| Partial provider success | Preserve successful identities; fail unresolved rows and resume only after reconciliation |
| Wrong version / prerelease / un-smoked artifact | No campaign activation |

Those route fixtures and browser QA remain unexecuted in this review. Use the
existing bmdpat release-email tests, a reviewed preview and 375/768/1440 rendering.
Owner test delivery and actual provider delivered/bounced/complained events
precede activation. The weekly editorial newsletter approval remains separate.

Owner choices: (1) authorize the bmdpat consent-selection/send-time fix using the
existing fields, with offline/preview proof before any activation; (2) leave the
Show Work campaign held until demand and the release packet justify the work.
Recommendation: option 1. Its strongest counterargument is spending integration
effort before qualifying outside repeat use is demonstrated. Revisit after the
October 13 verdict or a named release/cohort request.

#105 remains open: design/source review and sender tests are retained, while
consent/recovery fixtures, rendered QA, exact public artifact smoke and owner
delivery/activation are still required. No new sending authority is inferred.

Sign-off: OpenAI | GPT-6 | auto.
