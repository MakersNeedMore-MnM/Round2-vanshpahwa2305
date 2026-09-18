# QueryPeek — 3-Day Build Plan

## P0 — Must work

### Day 1: Core
- [ ] Environment works
- [ ] MySQL connection
- [ ] Read-only database role documented
- [ ] Schema introspection and caching
- [ ] LLM provider interface
- [ ] Natural language -> SQL
- [ ] SQLGlot parsing
- [ ] SELECT-only validation
- [ ] Multi-statement rejection
- [ ] Query timeout and row limit
- [ ] Basic execution
- [ ] Security unit tests

### Day 2: Product
- [ ] Streamlit UI
- [ ] Database status panel
- [ ] Question input
- [ ] SQL viewer
- [ ] Results table
- [ ] Basic chart selection
- [ ] Error handling
- [ ] SQL repair loop, max 2 retries
- [ ] Example questions
- [ ] Session query history

### Day 3: Demo + Deployment
- [ ] Deploy early
- [ ] Configure production secrets
- [ ] Populate demo database
- [ ] Test 10 normal queries
- [ ] Test 5 invalid queries
- [ ] Test 5 destructive queries
- [ ] Test 3 ambiguous queries
- [ ] Fix critical bugs
- [ ] Final README
- [ ] Architecture diagram
- [ ] Demo script
- [ ] Verify public URL

## P1 — Only after P0
- [ ] MySQL adapter
- [ ] SQLite adapter
- [ ] Better schema retrieval
- [ ] Query caching
- [ ] Authentication
- [ ] Saved queries
- [ ] Advanced charts
- [ ] Audit log

## Explicitly defer for MVP
- Vector DB unless demonstrably needed
- Fine-tuning
- Kubernetes
- Microservices
- React frontend
- Separate API deployment
- Enterprise RBAC
- Multi-tenant architecture
- Complex observability stack
- Full local LLM hosting
