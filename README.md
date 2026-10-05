# MrCOLOMBO OTTO inventory scheduler

This public repository contains only the minimal, non-proprietary scheduler for
the private MrCOLOMBO OTTO synchronization service. It does not contain access
credentials, product data, prices, customer data, or application source code.

The workflow starts the private synchronization endpoint every five minutes and
fails unless all 68 approved OTTO variants are resolved, active, and verified
without inventory, delivery, or order-ledger discrepancies.
