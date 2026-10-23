# MrCOLOMBO OTTO inventory scheduler

This public repository contains only the minimal, non-proprietary scheduler for
the private MrCOLOMBO OTTO synchronization service. It does not contain access
credentials, product data, prices, customer data, or application source code.

The workflow requests a run every five minutes. GitHub schedules are best-effort:
the observed median interval across the latest 97 runs on 23 October 2026 was
270 minutes. This workflow cannot guarantee a five-minute inventory sync.

Each invocation calls the private endpoint once, with a 240-second timeout and
no automatic mutation retries or authentication redirects. It fails unless all
68 approved variants pass the complete live inventory, delivery and ledger
checks. Failures report a safe reason and run ID where available, without raw
upstream response bodies, secrets or order data.

Local checks: `python3 -m unittest discover -s tests -v`.
