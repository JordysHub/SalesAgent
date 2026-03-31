# SalesAgent — Session Context

## What this project is

AI-powered RFP response system built for Accenture. Uploads RFP documents, automatically extracts questions, retrieves grounded answers from a knowledge base of proposal documents, verifies every claim against source material, and assembles a formatted proposal DOCX. Hosted on Azure, triggered via an Amethyst Studio company agent.

## Current state (as of 2026-03-31)

**Working end-to-end:**
- Ingestion pipeline — documents from Azure Blob → chunked → embedded → Qdrant vector store
- Ingestion registry — skips unchanged files on re-ingest, tracks chunk settings and timestamps
- RAG API — FastAPI on Azure Container Apps, three endpoints: `/health`, `/answer`, `/pipeline`
- `/answer` — retrieves chunks from Qdrant, synthesises grounded answer via LLM
- `/pipeline` — downloads RFP from blob, extracts questions via LLM, answers all, QA verifies, composes DOCX proposal, uploads to blob with 7-day SAS download URL. Output filename includes timestamp to prevent overwrites.
- Amethyst Studio agent — two actions: `search_knowledge_base` (/answer) and `generate_proposal` (/pipeline). Future of Amethyst as platform is uncertain — may be replaced.
- All pipeline parameters centralised in `src/config.py`, read from env vars
- LLM calls centralised in `src/utils/llm_client.py` — single `chat()` interface supporting `groq` and `azure_openai` providers, switchable via `LLM_PROVIDER` env var
- Local testing setup — `make serve` + `make ask-local`, reads `.env` directly
- GitHub Actions — `ingest.yml` (blob → Qdrant) and `deploy.yml` (Docker → Azure Container Apps)
- Tests — 14 tests in `tests/test_api.py`, pipeline tests marked `@pytest.mark.slow`
- Linting configured — Black, isort, flake8 via `make lint`

**Known issues / not yet fixed:**
- Amethyst Studio strips external URLs from agent responses — agent says "Download proposal" instead of showing the actual SAS URL
- Agent can fabricate sources and metadata when not forced to use `search_knowledge_base` — `formatted_response` fix deprioritised since Amethyst may be replaced
- `/pipeline` is synchronous — risk of Azure Container Apps 240s timeout on full 18-question runs

**Current knowledge base (fabricated test documents):**
- `accenture_company_profile.docx` — company overview, certifications, GDPR approach, 2 reference projects
- `accenture_team_profiles.docx` — team composition, 6 individual profiles
- `proposal_cloud_migration.docx` — GlobalBank NV cloud migration proposal
- `proposal_ai_customer.docx` — RetailMax AI customer intelligence proposal
- `proposal_cybersecurity.docx` — cybersecurity proposal
- `accenture_technical_architecture.docx` — intentionally NOT ingested (test coverage gap)

**Test RFP:** `data/rfp/RFP_TechCorp_AI_Platform_2026.docx` — 18 questions across 5 categories

---

## Key design decisions

- **No generative retrieval** — LLM only synthesises, never retrieves. Retrieval is deterministic vector search.
- **QA verification is structural** — dedicated step with retry loop, not a prompt instruction
- **Single unified Qdrant index** — one collection `rag_docs`, all documents
- **Registry pattern** — `registry.json` in blob tracks ingestion state, prevents redundant re-ingestion
- **Blob folder separation** — `documents/` for knowledge base, `rfp-inputs/` for RFPs, `rfp-outputs/` for proposals
- **All params in `src/config.py`** — single place to tune retrieval and generation behaviour
- **LLM provider abstraction** — all LLM calls go through `src/utils/llm_client.py`. Switch provider via `LLM_PROVIDER` env var (`groq` or `azure_openai`). Groq → Azure OpenAI migration requires only this file to change.
- **Embedding consistency** — `sentence-transformers/all-MiniLM-L6-v2` at ingestion and query time. Changing model requires full re-ingest.

---

## Azure resources

| Resource | Name |
|---|---|
| Container App | `rag-api` |
| Resource group | `rag-rg` |
| Storage account | `ragdocuments1337` |
| Blob container | `documents` |
| Container registry | `ragregistry1337.azurecr.io` |
| API URL | `https://rag-api.orangepond-15ea034f.northeurope.azurecontainerapps.io` |

---

## Repo structure

```
src/
  api.py                          ← FastAPI server (3 endpoints: /health, /answer, /pipeline)
  ingest.py                       ← ingestion entry point (run via GitHub Actions)
  config.py                       ← all tunable parameters
  utils/
    llm_client.py                 ← centralised LLM interface (chat() — groq + azure_openai)
    connector/
      blob_connector.py           ← Azure Blob access, registry load/save
      local_connector.py          ← local file walker (legacy, kept for local ingest)
    ingestion/
      parser.py                   ← DOCX/PDF/TXT parsing
      chunker.py                  ← text chunking
      embedder.py                 ← fastembed embedding
    store/
      vector_store.py             ← Qdrant client and upsert
    retrieval/
      retriever.py                ← vector search
    rfp/
      orchestrator.py             ← step 1: LLM extracts questions from RFP
      answer_agent.py             ← step 2: iterates questions, calls answer_question()
      answerer.py                 ← core RAG: retrieve + synthesise
      qa_verifier.py              ← step 3: verifies grounding, retries, flags
      composer.py                 ← step 4: assembles DOCX proposal

scripts/                          ← thin CLI wrappers
  ask.py                          ← query API, shows answer + config params
  run_pipeline.py                 ← run full pipeline locally
  inspect_chunks.py               ← inspect Qdrant index
  delete_source.py                ← delete chunks + registry entry
  ingest_source.py                ← targeted single-file ingest from blob
  show_registry.py                ← show ingestion registry
  debug_parse.py                  ← debug document parsing

tests/
  test_api.py                     ← 14 tests, pipeline tests marked @pytest.mark.slow

data/
  documents/                      ← knowledge base source files
  rfp/                            ← RFP input files
  rfp-outputs/                    ← generated proposals (gitignored)
  rfp-questions/                  ← extracted question JSON (gitignored)
```

---

## Tunable parameters (src/config.py + .env)

| Parameter | Default | Effect |
|---|---|---|
| `TOP_K` | 8 | Chunks retrieved per question |
| `MIN_SCORE` | 0.25 | Minimum similarity score threshold |
| `LOW_CONFIDENCE` | 0.3 | Avg score below this = low confidence flag |
| `TEMPERATURE` | 0.0 | LLM temperature (0 = deterministic) |
| `MAX_TOKENS` | 1024 | Max tokens in LLM response |
| `LLM_PROVIDER` | groq | LLM provider (`groq` or `azure_openai`) |
| `QA_MAX_RETRIES` | 2 | Max QA retry attempts |
| `QA_RETRY_TOP_K` | 3 | Extra chunks added on retry |
| `CHUNK_SIZE` | 256 | Tokens per chunk |
| `CHUNK_OVERLAP` | 40 | Token overlap between chunks |

Tune locally: change `.env`, restart server (`lsof -ti:8000 | xargs kill -9 && make serve`), test with `make ask-local`.
Tune on Azure without redeploying: `az containerapp update --name rag-api --resource-group rag-rg --set-env-vars TOP_K=10`

---

## Azure enterprise migration (blocked — no access yet)

Migration to company Azure tenant is the most important near-term workstream but is blocked on access/permissions with no ETA.

**Components to migrate:**
- Container App (`rag-api`)
- Blob Storage
- Container Registry (ACR)
- Groq → Azure OpenAI (company policy requirement — model TBD)

**Qdrant stays** — not migrating to Azure AI Search.

**Pre-migration prep already done:**
- LLM client abstracted into `llm_client.py` — switching to Azure OpenAI requires only env var changes and one file update

**Remaining prep to do before access arrives:**
- Add API authentication scaffolding (Entra ID / Bearer token)
- Document full migration checklist in NOTES.md

---

## Backlog

### Immediate (do next)
- [ ] Async `/pipeline` endpoint — return job ID immediately, poll `/pipeline/status/{job_id}`. Required before full 18-question RFP runs (current 240s timeout risk on Azure Container Apps).

### Near-term
- [ ] Proposal output design decisions — structure, section ordering, citation style, flagged answer handling
- [ ] Company DOCX template for composer — waiting for access to work laptop
- [ ] Company knowledge base ingestion — KB behind SSO at internal URL. Preferred approach: crawl and ingest into Qdrant. Blocked on identifying KB platform (SharePoint?) and auth method (service account / app registration).

### Later
- [ ] Reranking layer (after real data)
- [ ] Query decomposition (after real data)
- [ ] Switch to OpenAI embeddings + Azure AI Search for production
- [ ] Vision LLM for image ingestion
- [ ] Automated document lifecycle (blob deletions → Qdrant)
- [ ] Event Grid trigger on blob upload
- [ ] Log Analytics workspace
- [ ] Azure enterprise migration (execute once access granted)

### Done this session (2026-03-31)
- [x] Timestamp added to proposal output filename
- [x] `sys.path.insert` hacks removed from all scripts
- [x] LLM calls centralised into `src/utils/llm_client.py` with `chat()` interface — supports `groq` and `azure_openai`, switchable via `LLM_PROVIDER` env var
- [x] `MAX_TOKENS` and `LLM_PROVIDER` added to `config.py` and `.env.example`
- [x] Linting configured — Black, isort, flake8 via `make lint`
- [x] Unused imports and broken f-strings cleaned up across all files
- [x] Test suite expanded from 8 to 14 tests — added source citation check, chunk count, top_k, low confidence, timestamp format, URL expiry format
- [x] `actions/checkout` bumped to v4 in `deploy.yml` (Node.js 24 compatibility, required before June 2026)

---

## How to continue in a new chat

Paste this file and say: "Continue working on SalesAgent. Here is the current context."
For full command reference, also paste `NOTES.md` or ask for a specific section.