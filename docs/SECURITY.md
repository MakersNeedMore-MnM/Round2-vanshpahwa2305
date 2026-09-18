# QueryPeek Security

## Threat model
The LLM is untrusted. Generated SQL may be incorrect or unsafe.

## Required controls
1. Parse SQL using SQLGlot or another AST-capable parser.
2. Allow SELECT only for the MVP.
3. Reject INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, TRUNCATE, GRANT, REVOKE, unsafe transaction/control statements, and multiple statements.
4. Use a dedicated MySQL read-only role.
5. Apply query timeout and row/result limits.
6. Never commit API keys, passwords, or credential-bearing URLs.
7. Never log secrets or full sensitive datasets.
8. Prefer schema/metadata context over raw rows for LLM prompts.

## Required tests
- SELECT allowed
- INSERT blocked
- UPDATE blocked
- DELETE blocked
- DROP blocked
- ALTER blocked
- multiple statements blocked
- comment/whitespace edge cases
- dialect-specific syntax
