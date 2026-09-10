Booking Constants Proposal
Generated: 2026-09-08

Purpose
- Capture canonical booking `status`, `payment_status`, and `booking_source` values observed in codebase.
- Propose a `booking_constants.py` shape (read-only proposal) and alias-mapping strategy for a non-invasive rollout.

1) Canonical values (proposal)

- STATUS
  - DRAFT = 'draft'
  - PENDING = 'pending'
  - PENDING_REVIEW = 'pending_review'
  - PENDING_QUOTATION = 'pending_quotation'
  - PENDING_PAYMENT = 'pending_payment'
  - AWAITING_PAYMENT = 'awaiting_payment'
  - AWAITING_CUSTOMER = 'awaiting_customer'
  - AWAITING_CATERER = 'awaiting_caterer'
  - CONFIRMED = 'confirmed'
  - PREPARING = 'preparing'
  - READY_FOR_DELIVERY = 'ready_for_delivery'
  - ON_THE_WAY = 'on_the_way'
  - ARRIVED = 'arrived'
  - SETUP_ONGOING = 'setup_ongoing'
  - IN_PROGRESS = 'in_progress'
  - COMPLETED = 'completed'
  - CANCELLED = 'cancelled'
  - REJECTED = 'rejected'
  - EXPIRED = 'expired'
  - UNDER_DISPUTE = 'under_dispute'
  - RELEASED = 'released'
  - INQUIRY = 'inquiry'
  - TENTATIVE = 'tentative'
  - NEGOTIATING = 'negotiating'
  - QUOTED = 'quoted'

- PAYMENT_STATUS
  - PENDING = 'pending'
  - UNPAID = 'unpaid'
  - PENDING_VERIFICATION = 'pending_verification'
  - PROOF_SUBMITTED = 'proof_submitted'
  - BALANCE_PROOF_SUBMITTED = 'balance_proof_submitted'
  - REUPLOAD_REQUESTED = 'reupload_requested'
  - BALANCE_REUPLOAD_REQUESTED = 'balance_reupload_requested'
  - VERIFIED = 'verified'
  - DEPOSIT_PAID = 'deposit_paid'  # downpayment/reservation
  - PARTIAL_PAID = 'partially_paid' # normalize partially_paid/partial_paid
  - PAID = 'paid'  # fully paid
  - OVERDUE = 'overdue'
  - FULLY_PAID = 'fully_paid' # alias for 'paid'

- BOOKING_SOURCE (examples)
  - OCCASERVE = 'OccaServe'  # DB default
  - WALKIN = 'Walk-in'
  - FACEBOOK = 'Facebook'
  - PHONE = 'Phone Call'
  - INTERNAL = 'Internal'
  - OTHER = 'Other'
  - OCCASERVE_PLATFORM = 'OccaServe Platform'  # display variant

2) Alias maps (runtime translation, no DB migration)

- PAYMENT_STATUS_ALIASES = {
    'fully_paid': 'paid',
    'fully-paid': 'paid',
    'partial_paid': 'partially_paid',
    'partial': 'partially_paid',
    'downpayment_paid': 'deposit_paid',
    'downpayment': 'deposit_paid'
}

- SOURCE_TO_ENTRY_METHOD = {
    'Walk-in': 'walkin',
    'Internal': 'internal',
    'OccaServe': 'online',
    'OccaServe Platform': 'online',
    'Facebook': 'online',
    'Phone Call': 'walkin',
    'Other': 'other'
}

3) `booking_constants.py` shape (proposal)

- Provide constants and helper functions:

  STATUS = { 'DRAFT': 'draft', ... }
  PAYMENT = { 'PENDING': 'pending', ... }
  SOURCE = { 'OCCASERVE': 'OccaServe', ... }

  PAYMENT_ALIAS_MAP = {...}
  SOURCE_ENTRY_MAP = {...}

  def normalize_payment_status(value: str) -> str:
      # return canonical value; tolerate None/unknown

  def entry_method_from_source(source: str) -> str:
      # return 'online'|'walkin'|'internal'|'other'

4) Rollout plan (non-invasive, minimal risk)

- Phase 0 (read-only research): commit this proposal, run tests.
- Phase 1 (mapping layer): add `booking_constants.py` and use helper functions only at HTTP API boundaries and in templates rendering contexts. Do NOT change DB values. Update `bookings.js` to consume server-provided entry_method where appropriate.
- Phase 2 (refactor internals): gradually replace scattered string checks to reference `booking_constants` values (code-level refactors), running tests after each small change.
- Phase 3 (optional migration): after full coverage and monitoring, run a reversible DB migration updating legacy aliases to canonical values; deploy code that accepts both during deprecation window.

5) Tests & verification

- Add unit tests for `normalize_payment_status()` and `entry_method_from_source()`.
- Add integration tests for `create_manual_booking` and `alacarte_submit` to assert expected normalized outputs without altering DB rows.
- Add smoke test that templates/JS see `entry_method` in API JSON responses.

6) Implementation notes & risks

- Do not rename DB column names or current values without migration scripts and migration window.
- Payment transitions (AI verification paths) are high-risk — centralize logic into a single service (e.g., `PaymentStateManager`) before changing stored values.
- Shadow user patterns (walk-ins) affect reporting; consider a normalization step to treat `Walk-in` booking_source specially in analytics.

7) Next actions I can perform now (pickable)
- Create a draft `booking_constants.py` in `OccaShare/app/constants/` implementing the above with helper functions and tests. (I will not change other files.)
- Update `bookings` JSON endpoints to include `entry_method` derived from `booking_source` (read-only change to responses). 

----

If you want me to proceed, pick one: (A) create `booking_constants.py` + unit tests, or (B) update APIs to return `entry_method` now.