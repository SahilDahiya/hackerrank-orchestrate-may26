# Mental Model

This repo is a ticket-handling runtime with a coding-agent shape.

It is not a chat app.
It is not a general-purpose agent platform.
It is not primarily a retrieval pipeline.

The basic loop is:

```text
batch CLI
  -> load support_tickets.csv
  -> for each ticket:
       create fresh session
       run agent with scoped read-only tools over data/
       collect final decision/result
       validate result
       write one row to output.csv
  -> end
```

`code/main.py` is the evaluator-facing entry point.

Everything behind that file is an internal implementation boundary, not the
submission contract itself.

The agent's job inside one ticket is:

1. understand the ticket
2. inspect the local support corpus through tools
3. decide whether to reply or escalate
4. produce a grounded result

The host's job is:

1. manage batch execution
2. manage session boundaries
3. enforce scope
4. validate outputs
5. write the CSV

That separation is intentional. The model explores and decides. The host owns
the contract.
