# MrCOLOMBO OTTO inventory scheduler

This public repository contains only the minimal, non-proprietary timers for
the private synchronization service. No credentials, product data, prices,
customer data or proprietary application source are included.

The primary timer is the small Cloudflare Worker in `cloudflare/`, deployed in
the owner's existing account with `*/5 * * * *`. It has no public HTTP route.
Secrets are configured only through protected runtime storage. Its separate
machine key can authorize only `POST /api/sync`, never catalog activation.

The GitHub workflow is retained for manual fallback. Before replacement, its
configured five-minute schedule actually ran at a median interval of 270 minutes
across the latest 97 runs on 23 October 2026. A cron configuration alone is not
proof of execution: verify actual persisted runs and fresh inventory readback.

Both timers call the service once per invocation, with a 240-second timeout and
no automatic POST retry or authentication redirect. Success requires all 68
approved variants to pass the complete live inventory, delivery and ledger checks.
Logs contain only safe reasons, validated run IDs and allowed counters. Raw
upstream bodies, private SKU diagnostics and credentials are never logged.

Local checks:

- `python3 -m unittest discover -s tests -v`
- `node --test cloudflare/worker.test.mjs`

Deployment ordering: stage a new Worker with an explicit empty cron list and
public/preview URLs disabled; supply its two secrets through stdin; deploy the
private service's timer authorization; then deploy the final cron configuration.
The checked-in configuration enables the cron, so it is not a staging config.
Do not create a second active timer until the prior writer and exclusivity are
verified. After observing successful automatic runs, retain GitHub as manual-only.
To stop the Worker reversibly, deploy the same configuration with `crons: []`.
No paid plan activation or installation of a Shopify app is required.
