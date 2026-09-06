# Sample Events — Read Before Using

`events.json` / `events.csv` in this folder are **real output from the
actual pipeline** (not hand-written mock data) — but they should currently
be treated as **schema examples, not accuracy-validated results**.

Why: the product-detection layer feeding these events has a known failure
mode on busy warehouse scenes (see
`computer_vision/data/annotations/detection_findings.md`). A fix is built
but not yet validated. Expect the `throwing` behaviour in particular to be
over-reported here.

Use this file to:
- Build/test frontend components against the real field shapes and types
- Build/test a backend endpoint that serves this shape

Do NOT use this file to:
- Demo "the system detected N incidents" as a real accuracy claim
- Tune UI thresholds/expectations around these specific counts

This file will be regenerated once product detection is validated - re-pull
before a real demo.
