# ─── Local Development ─────────────────────────────────────────────────────
serve:
	uvicorn src.api:app --reload --port 8000

ask:
	python scripts/ask.py "$(Q)" --show-chunks --top-k 10

# ─── RFP Pipeline ──────────────────────────────────────────────────────────
rfp:
	python scripts/run_pipeline.py --file $(F) --output proposal_output.docx --save-questions rfp_questions.json --max-questions 5 --top-k 8

# ─── Knowledge Base ────────────────────────────────────────────────────────
inspect:
	python scripts/inspect_chunks.py

inspect-file:
	python scripts/inspect_chunks.py --file $(F)

duplicates:
	python scripts/inspect_chunks.py --duplicates

registry:
	python scripts/show_registry.py

upload:
	az storage blob upload-batch \
		--account-name ragdocuments1337 \
		--destination documents \
		--source data/documents \
		--account-key $$(grep AZURE_STORAGE_KEY .env | cut -d= -f2-) \
		--overwrite false

# ─── Ingestion ─────────────────────────────────────────────────────────────
ingest:
	python -m src.ingest

publish:
	az storage blob upload-batch \
		--account-name ragdocuments1337 \
		--destination documents \
		--source data/documents \
		--account-key $$(grep AZURE_STORAGE_KEY .env | cut -d= -f2-) \
		--overwrite false
	gh workflow run ingest.yml && gh run watch

ingest-file:
	python scripts/ingest_source.py --file $(F)

delete:
	python scripts/delete_source.py $(F)

delete-all:
	python scripts/delete_source.py --all

# ─── Debugging ─────────────────────────────────────────────────────────────
debug:
	python scripts/debug_parse.py --file $(F)

# ─── Deployment ────────────────────────────────────────────────────────────
deploy:
	gh workflow run deploy.yml && gh run watch

sync:
	gh workflow run ingest.yml && gh run watch

release:
	gh workflow run ingest.yml && gh run watch
	gh workflow run deploy.yml && gh run watch

# ─── Logs ──────────────────────────────────────────────────────────────────
logs:
	az containerapp logs show --name rag-api --resource-group rag-rg --follow --tail 50

logs-history:
	az containerapp logs show --name rag-api --resource-group rag-rg --tail 200 | grep "endpoint="