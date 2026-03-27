# SalesAgent — Project Notes & Command Reference

## Project Overview

AI-powered RFP response system that automatically generates proposal documents from uploaded RFP files. Built on a retrieval-augmented generation (RAG) architecture where every claim in the generated proposal is traceable to a real source document.

**Stack:**
- FastAPI API — hosted on Azure Container Apps
- Qdrant — vector store (cloud-hosted)
- all-MiniLM-L6-v2 — embedding model (via fastembed)
- Groq (llama-3.3-70b-versatile) — LLM for answer generation and orchestration
- Azure Blob Storage — document storage (knowledge base + RFPs + proposals)
- GitHub Actions — CI/CD for ingestion and deployment
- Amethyst Studio — company agent platform

**Azure resources:**
- Container App: `rag-api` | Resource group: `rag-rg`
- Storage account: `ragdocuments1337` | Container: `documents`
- API URL: `https://rag-api.orangepond-15ea034f.northeurope.azurecontainerapps.io`

---

## Architecture

```
RFP Document (blob: rfp-inputs/)
        ↓
Orchestrator        — LLM extracts questions from RFP
        ↓
Answer Agent        — calls /answer per question, retrieves from Qdrant
        ↓
QA Verifier         — checks grounding, retries on failure, flags gaps
        ↓
Composer            — assembles verified answers into DOCX proposal
        ↓
Proposal (blob: rfp-outputs/)
```

**Blob folder structure:**
```
documents/
  ├── *.docx / *.pdf         ← knowledge base documents
  ├── rfp-inputs/            ← uploaded RFP files
  ├── rfp-outputs/           ← generated proposals
  └── registry.json          ← ingestion registry (auto-managed)
```

**Local folder structure:**
```
data/
  ├── documents/             ← knowledge base source files
  ├── rfp/                   ← RFP input files
  ├── rfp-outputs/           ← generated proposals (local, gitignored)
  └── rfp-questions/         ← extracted question JSON files (local, gitignored)
```

---

## Makefile Commands

### Git
| Command | Description |
|---|---|
| `make push M="message"` | Stage all, commit, push |

### Local Development
| Command | Description |
|---|---|
| `make serve` | Start API server locally with auto-reload on port 8000 |
| `make ask Q="question"` | Query the Azure API, show chunks |
| `make ask-local Q="question"` | Query the local server, show chunks |

### RFP Pipeline
| Command | Description |
|---|---|
| `make rfp F="path/to/rfp.docx"` | Run full pipeline locally, max 5 questions |
| `make pipeline F="filename.docx" Q=3` | Call live Azure /pipeline endpoint, Q = max questions |
| `make download-proposal F="rfp_filename.docx"` | Download generated proposal from blob and open |

### Knowledge Base
| Command | Description |
|---|---|
| `make inspect` | Show all sources, chunk counts, settings, ingest dates |
| `make inspect-file F="filename.docx"` | Inspect chunks for a single source |
| `make duplicates` | Check for duplicate chunks in the store |
| `make registry` | Show ingestion registry from blob |

### Ingestion
| Command | Description |
|---|---|
| `make ingest` | Run ingestion pipeline locally (reads from blob, skips unchanged) |
| `make ingest-file F="filename.docx"` | Delete + re-ingest a single file from blob |
| `make upload` | Upload new files from data/documents/ to blob (skips existing) |
| `make upload-rfp F="filename.docx"` | Upload RFP from data/rfp/ to blob rfp-inputs/ |
| `make publish` | Upload new documents + trigger ingest workflow |
| `make delete F="filename.docx"` | Delete all chunks for a source from Qdrant + registry |
| `make delete-all` | Delete all chunks from Qdrant + clear registry (with confirmation) |

### Debugging
| Command | Description |
|---|---|
| `make debug F="filename.docx"` | Parse a document and show extracted text + character count |

### Deployment
| Command | Description |
|---|---|
| `make deploy` | Trigger deploy workflow + watch |
| `make sync` | Trigger ingest workflow + watch |
| `make release` | Trigger ingest + deploy sequentially |

### Tests
| Command | Description |
|---|---|
| `make test` | Run all tests except slow pipeline tests |
| `make test-full` | Run all tests including pipeline tests (costs tokens) |

### Logs
| Command | Description |
|---|---|
| `make logs` | Stream live Azure container logs (last 50 lines) |
| `make logs-history` | Show last 200 log lines, filtered to endpoint calls only |

---

## Parameter Tuning

All tunable parameters are centralised in `src/config.py` and read from environment variables.

### Parameters

| Parameter | Default | Description |
|---|---|---|
| `TOP_K` | 8 | Chunks retrieved per question. Higher = more context, more noise |
| `MIN_SCORE` | 0.25 | Minimum similarity score to include a chunk. Higher = stricter |
| `LOW_CONFIDENCE` | 0.3 | Avg score below this flags answer as low confidence |
| `TEMPERATURE` | 0.0 | LLM temperature. 0 = deterministic, 0.5 = more varied |
| `QA_MAX_RETRIES` | 2 | Max retries for failed QA verification |
| `QA_RETRY_TOP_K` | 3 | Extra chunks added to top_k on each retry |
| `CHUNK_SIZE` | 256 | Tokens per chunk at ingestion time |
| `CHUNK_OVERLAP` | 40 | Token overlap between chunks |
| `EMBED_MODEL` | sentence-transformers/all-MiniLM-L6-v2 | Embedding model |
| `GROQ_MODEL` | llama-3.3-70b-versatile | LLM model |

### How to tune locally

1. Change value in `.env`
2. Restart local server: `lsof -ti:8000 | xargs kill -9 && make serve`
3. Test: `make ask-local Q="your question"`
4. Output shows current config values below the answer

### How to tune on Azure (no redeploy needed)

```bash
az containerapp update \
  --name rag-api \
  --resource-group rag-rg \
  --set-env-vars TOP_K=10 TEMPERATURE=0.2
```

Takes effect in ~30 seconds.

### How to deploy param changes permanently

Update the value in `.github/workflows/deploy.yml` under `--set-env-vars`, then:
```bash
make push M="tune TOP_K to 10"
gh workflow run deploy.yml
```

---

## Local vs Azure Testing

| Scenario | Command | Notes |
|---|---|---|
| Test code changes locally | `make serve` + `make ask-local` | Reads `.env`, free, instant |
| Test against live Azure | `make ask` | Hits deployed container |
| Run full pipeline locally | `make rfp F="..."` | Reads `.env`, costs Groq tokens |
| Run full pipeline on Azure | `make pipeline F="..." Q=3` | Hits deployed container |
| Run tests | `make test` | Tests against Azure by default |

---

## Terminal Commands

### API — Direct curl calls
```bash
# Health check
curl https://rag-api.orangepond-15ea034f.northeurope.azurecontainerapps.io/health

# Stats (total chunks in store)
curl https://rag-api.orangepond-15ea034f.northeurope.azurecontainerapps.io/stats

# Answer a question
curl -X POST https://rag-api.orangepond-15ea034f.northeurope.azurecontainerapps.io/answer \
  -H "Content-Type: application/json" \
  -d '{"question": "your question here", "top_k": 5}'

# Run full pipeline
curl -X POST https://rag-api.orangepond-15ea034f.northeurope.azurecontainerapps.io/pipeline \
  -H "Content-Type: application/json" \
  -d '{"filename": "RFP_TechCorp_AI_Platform_2026.docx", "top_k": 8, "max_questions": 3}'
```

### GitHub Actions
```bash
# Trigger workflows
gh workflow run ingest.yml
gh workflow run ingest.yml --ref feature/branch-name
gh workflow run deploy.yml

# Watch a run
gh run watch
gh run watch $(gh run list --workflow="ingest.yml" --limit 1 --json databaseId -q '.[0].databaseId')

# View logs for a specific run
gh run view <run-id> --log | grep -E "Skipping|Processing|registry|chunks|error"

# List recent runs
gh run list --workflow="ingest.yml" --limit 5
gh run list --workflow="deploy.yml" --limit 5
```

### Azure — Container App
```bash
# View env vars on container
az containerapp show \
  --name rag-api \
  --resource-group rag-rg \
  --query "properties.template.containers[0].env" \
  --output table

# List secrets
az containerapp secret list \
  --name rag-api \
  --resource-group rag-rg \
  --output table

# Add a secret
az containerapp secret set \
  --name rag-api \
  --resource-group rag-rg \
  --secrets "key-name=value"

# Set env var referencing a secret
az containerapp update \
  --name rag-api \
  --resource-group rag-rg \
  --set-env-vars KEY=secretref:key-name

# Tune params without redeploying
az containerapp update \
  --name rag-api \
  --resource-group rag-rg \
  --set-env-vars TOP_K=10 TEMPERATURE=0.2 MIN_SCORE=0.3
```

### Azure — Blob Storage
```bash
# List blobs
az storage blob list \
  --account-name ragdocuments1337 \
  --container-name documents \
  --account-key $(grep AZURE_STORAGE_KEY .env | cut -d= -f2-) \
  --query "[].name" \
  --output table

# Upload single file
az storage blob upload \
  --account-name ragdocuments1337 \
  --container-name documents \
  --name rfp-inputs/filename.docx \
  --file data/rfp/filename.docx \
  --account-key $(grep AZURE_STORAGE_KEY .env | cut -d= -f2-)

# Upload batch
az storage blob upload-batch \
  --account-name ragdocuments1337 \
  --destination documents \
  --source data/documents \
  --account-key $(grep AZURE_STORAGE_KEY .env | cut -d= -f2-) \
  --overwrite false

# Download file
az storage blob download \
  --account-name ragdocuments1337 \
  --container-name documents \
  --name rfp-outputs/proposal_filename.docx \
  --file proposal_output.docx \
  --account-key $(grep AZURE_STORAGE_KEY .env | cut -d= -f2-)

# Delete a blob
az storage blob delete \
  --account-name ragdocuments1337 \
  --container-name documents \
  --name filename.docx \
  --account-key $(grep AZURE_STORAGE_KEY .env | cut -d= -f2-)

# Get storage key
az storage account keys list \
  --account-name ragdocuments1337 \
  --resource-group rag-rg \
  --query "[0].value" \
  --output tsv
```

### Qdrant — Direct API
```bash
# Check collection status and vector count
curl -X GET "$(grep QDRANT_URL .env | cut -d= -f2)/collections/rag_docs" \
  -H "api-key: $(grep QDRANT_API_KEY .env | cut -d= -f2)"
```

### Local server
```bash
# Kill process on port 8000 and restart
lsof -ti:8000 | xargs kill -9 && make serve
```

---

## Scripts Reference

| Script | Usage | Description |
|---|---|---|
| `scripts/ask.py` | `python scripts/ask.py "question" --show-chunks` | Query the API |
| `scripts/inspect_chunks.py` | `python scripts/inspect_chunks.py [--file name] [--duplicates]` | Inspect Qdrant index |
| `scripts/delete_source.py` | `python scripts/delete_source.py filename.docx` or `--all` | Delete chunks + registry entry |
| `scripts/ingest_source.py` | `python scripts/ingest_source.py --file filename.docx` | Delete + re-ingest single file from blob |
| `scripts/show_registry.py` | `python scripts/show_registry.py` | Show ingestion registry contents |
| `scripts/debug_parse.py` | `python scripts/debug_parse.py --file filename.docx` | Debug document parsing |
| `scripts/run_pipeline.py` | `python scripts/run_pipeline.py --file path/to/rfp.docx --max-questions 5` | Run full pipeline locally |

---

## Environment Variables (.env)

```
# Secrets
QDRANT_URL=
QDRANT_API_KEY=
GROQ_API_KEY=
AZURE_STORAGE_KEY=

# Non-sensitive config
GROQ_MODEL=llama-3.3-70b-versatile
EMBED_MODEL=sentence-transformers/all-MiniLM-L6-v2
CHUNK_SIZE=256
CHUNK_OVERLAP=40
DOCS_PATH=./data/documents
AZURE_STORAGE_ACCOUNT=ragdocuments1337
AZURE_CONTAINER_NAME=documents
SAS_EXPIRY_DAYS=7

# Tunable params
TOP_K=8
MIN_SCORE=0.25
LOW_CONFIDENCE=0.3
TEMPERATURE=0.0
QA_MAX_RETRIES=2
QA_RETRY_TOP_K=3

# Local testing
API_URL=https://rag-api.orangepond-15ea034f.northeurope.azurecontainerapps.io
```

---

## Agent Configuration (Amethyst Studio)

### Action 1 — search_knowledge_base
```json
{
  "name": "search_knowledge_base",
  "description": "ALWAYS call this tool first before answering ANY question. Searches the internal Accenture knowledge base containing proposal documents, service descriptions, project experience, and investment figures. Never answer from memory — always retrieve from this tool first.",
  "api": {
    "url": "https://rag-api.orangepond-15ea034f.northeurope.azurecontainerapps.io/answer",
    "method": "POST",
    "auth": "none",
    "headers": {
      "Content-Type": "application/json",
      "X-Client-ID": "company-agent"
    }
  },
  "parameters": {
    "type": "object",
    "properties": {
      "question": {
        "type": "string",
        "description": "The question to search for in the knowledge base."
      },
      "top_k": {
        "type": "number",
        "description": "Number of chunks to retrieve. Always use 10."
      }
    },
    "required": ["question"]
  }
}
```

### Action 2 — generate_proposal
```json
{
  "name": "generate_proposal",
  "description": "Generate a full proposal document in response to an RFP. Call this when the user asks to generate or create a proposal and provides an RFP filename. When the function returns, always present: (1) questions extracted, answered, verified, flagged counts, (2) the full output_url as plain text starting with https://, (3) the output_url_expires date.",
  "api": {
    "url": "https://rag-api.orangepond-15ea034f.northeurope.azurecontainerapps.io/pipeline",
    "method": "POST",
    "auth": "none",
    "headers": {
      "Content-Type": "application/json",
      "X-Client-ID": "company-agent"
    }
  },
  "parameters": {
    "type": "object",
    "properties": {
      "filename": {
        "type": "string",
        "description": "The RFP filename in blob storage (e.g. RFP_TechCorp_AI_Platform_2026.docx)"
      },
      "top_k": {
        "type": "number",
        "description": "Number of chunks to retrieve per question. Use 8."
      },
      "max_questions": {
        "type": "number",
        "description": "Maximum number of RFP questions to answer. Set to 0 to answer all. Use 3-5 for a quick test."
      }
    },
    "required": ["filename"]
  },
  "earlyExit": false,
  "streamingEnabled": false,
  "isContextPrimer": false,
  "dsAuthEnabled": false
}
```

---

## Testing Checklist

### API health
```bash
curl https://rag-api.orangepond-15ea034f.northeurope.azurecontainerapps.io/health
curl https://rag-api.orangepond-15ea034f.northeurope.azurecontainerapps.io/stats
```

### Knowledge base
```bash
make inspect
make registry
make duplicates
```

### Retrieval quality
```bash
make ask-local Q="what services does Accenture offer?"
make ask-local Q="describe the GlobalBank migration project"
make ask-local Q="what is Accenture's approach to GDPR compliance?"
```

### Run tests
```bash
make test
make test-full  # includes pipeline tests — costs tokens
```

### Pipeline (local)
```bash
make rfp F="data/rfp/RFP_TechCorp_AI_Platform_2026.docx"
```

### Pipeline (Azure via agent)
In Amethyst Studio chat:
> "Use generate_proposal function: RFP_TechCorp_AI_Platform_2026.docx, max 3 questions"

### Pipeline (Azure via curl)
```bash
make pipeline F="RFP_TechCorp_AI_Platform_2026.docx" Q=3
```

### Download proposal
```bash
make download-proposal F="RFP_TechCorp_AI_Platform_2026.docx"
```

---

## Backlog

### Immediate
- [ ] Fix agent not returning raw SAS URL — Amethyst Studio strips external URLs
- [ ] Add timestamp to proposal output filename to preserve version history
- [ ] Add length instruction to system prompt in answerer.py for more comprehensive answers
- [ ] Remove all `sys.path.insert` lines now that `pip install -e .` is in place

### Pipeline Improvements
- [ ] Save intermediate results (answers JSON) to disk so composer can rerun without re-answering
- [ ] Async `/pipeline` endpoint — return job ID immediately, poll `/pipeline/status/{job_id}`
- [ ] Company DOCX template for proposal composer output — waiting for laptop access

### Retrieval Quality (after real data)
- [ ] Reranking layer — cross-encoder reranker after top-k retrieval
- [ ] Query decomposition — 3–5 sub-queries per question, merge results
- [ ] Switch to OpenAI embeddings (text-embedding-3-large, 1536 dimensions)
- [ ] Switch vector store to Azure AI Search for production
- [ ] Tune TOP_K, CHUNK_SIZE, MIN_SCORE against real document corpus

### Knowledge Base Management
- [ ] Automated document lifecycle — blob deletions propagate to Qdrant + registry
- [ ] Event Grid trigger on blob upload to auto-fire ingest workflow
- [ ] `make registry` diff against `make inspect` to flag inconsistencies
- [ ] `delete_source.py` warn if deleted file still exists in blob

### Infrastructure & DevOps
- [ ] Log Analytics workspace for persistent queryable logs
- [ ] Node.js 24 upgrade for GitHub Actions (required before June 2026)
- [ ] User Delegation SAS for production (replaces account key SAS)
- [ ] Add smoke test to ingest workflow — assert chunk count > 0

### Access & Onboarding
- [ ] Azure Storage Explorer setup guide for team members
- [ ] Document blob folder structure and naming conventions

### Tests to Add
- [ ] Unit test for qa_verifier logic
- [ ] Unit test for chunker
- [ ] Unit test for parser
- [ ] Unit test for embedder — assert vector length 384
- [ ] Unit test for orchestrator — assert question structure
- [ ] Version endpoint `/version` returning git commit SHA

### Azure Enterprise Migration
- [ ] Azure subscription onboarding to company tenant
- [ ] Migrate ACR, Container App, Blob Storage to company subscription
- [ ] Switch Qdrant cloud to Azure AI Search
- [ ] Replace Groq with Azure OpenAI for company policy compliance
- [ ] Add authentication to API endpoints (Azure AD / Entra ID)
- [ ] Managed Identity for blob access (replaces storage account key)
- [ ] SharePoint ingestion via Microsoft Graph API
- [ ] Re-register Amethyst Studio actions with new URLs

### Proposal Output Design (before company template)

- [ ] Decide on proposal structure — cover page, table of contents, section per RFP category, or flat Q&A
- [ ] Decide on answer format — full paragraphs vs bullet points vs mixed
- [ ] Decide on source citation style — inline [source.docx], footnotes, or reference list at end of section
- [ ] Decide whether flagged/unverified answers are included with warning, excluded entirely, or shown as "to be completed"
- [ ] Decide on confidence indicators — show avg score per answer, show low confidence warning, or hide entirely from final output
- [ ] Decide on metadata in output — date generated, RFP filename, questions answered/flagged counts, or clean document only
- [ ] Define section order — follow RFP category order or reorder by Accenture's preferred proposal structure
- [ ] Once decisions are made, update src/utils/rfp/composer.py accordingly
- [ ] When company DOCX template is available, wire it in as the base document