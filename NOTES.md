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
| `make ask Q="question"` | Query the local API, show chunks, top-k 10 |

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

### Logs
| Command | Description |
|---|---|
| `make logs` | Stream live Azure container logs (last 50 lines) |
| `make logs-history` | Show last 200 log lines, filtered to endpoint calls only |

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

---

## Scripts Reference

| Script | Usage | Description |
|---|---|---|
| `scripts/ask.py` | `python scripts/ask.py "question" --top-k 10 --show-chunks --endpoint answer` | Query the API locally |
| `scripts/inspect_chunks.py` | `python scripts/inspect_chunks.py [--file name] [--duplicates]` | Inspect Qdrant index |
| `scripts/delete_source.py` | `python scripts/delete_source.py filename.docx` or `--all` | Delete chunks + registry entry |
| `scripts/ingest_source.py` | `python scripts/ingest_source.py --file filename.docx` | Delete + re-ingest single file from blob |
| `scripts/show_registry.py` | `python scripts/show_registry.py` | Show ingestion registry contents |
| `scripts/debug_parse.py` | `python scripts/debug_parse.py --file filename.docx` | Debug document parsing |
| `scripts/run_pipeline.py` | `python scripts/run_pipeline.py --file path/to/rfp.docx --max-questions 5 --top-k 8` | Run full pipeline locally |

---

## Environment Variables (.env)

```
QDRANT_URL=
QDRANT_API_KEY=
GROQ_API_KEY=
GROQ_MODEL=llama-3.3-70b-versatile
EMBED_MODEL=all-MiniLM-L6-v2
CHUNK_SIZE=256
CHUNK_OVERLAP=40
DOCS_PATH=./data/documents
AZURE_STORAGE_ACCOUNT=ragdocuments1337
AZURE_STORAGE_KEY=
AZURE_CONTAINER_NAME=documents
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
  "description": "Generate a full proposal document in response to an RFP. Call this when the user asks to generate or create a proposal and provides an RFP filename. Always include the full output_url from the response as a clickable download link for the user.",
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
  }
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
python scripts/ask.py "what services does Accenture offer?" --show-chunks --top-k 10
python scripts/ask.py "describe the cloud migration project" --show-chunks --top-k 10
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

- Automated document lifecycle: blob deletions propagate to Qdrant + registry automatically
- Event Grid trigger on blob upload to auto-fire ingest workflow
- Log Analytics workspace for persistent queryable logs (30-day retention)
- Reranking layer for improved retrieval precision
- Vision LLM for image and scanned document ingestion at ingest time
- Switch to OpenAI embeddings (text-embedding-3-large) + Azure AI Search for production
- Company DOCX template for proposal composer output
- Proposal versioning — timestamp in filename to preserve history
- Azure Storage Explorer setup guide for team members to upload RFPs
- User Delegation SAS for production (replaces account key SAS)
- `make delete-all` --force flag for CI use without confirmation prompt
- `make registry` diff against `make inspect` to flag inconsistencies
- `delete_source.py` warn if file still exists in blob after chunk deletion
- Node.js 24 upgrade for GitHub Actions (required before June 2026)
- Async `/pipeline` endpoint with job ID + polling for long-running proposals
