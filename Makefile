# ─── Git ───────────────────────────────────────────────────────────────────
push:
	git add .
	git commit -m "$(M)"
	git push

# ─── Local Development ─────────────────────────────────────────────────────
serve:
	uvicorn src.api:app --reload --port 8000

ask:
	python scripts/ask.py "$(Q)" --show-chunks --top-k 10

ask-local:
	API_URL=http://localhost:8000 python scripts/ask.py "$(Q)" --show-chunks

# ─── RFP Pipeline ──────────────────────────────────────────────────────────
rfp:
	python scripts/run_pipeline.py --file $(F) --output data/rfp-outputs/proposal_output.docx --save-questions data/rfp-questions/rfp_questions.json --max-questions 5 --top-k 8

pipeline:
	curl -X POST https://rag-api.orangepond-15ea034f.northeurope.azurecontainerapps.io/pipeline \
		-H "Content-Type: application/json" \
		-d '{"filename": "$(F)", "top_k": 8, "max_questions": $(Q)}'

download-proposal:
	az storage blob download \
		--account-name ragdocuments1337 \
		--container-name documents \
		--name rfp-outputs/proposal_$(F) \
		--file proposal_output.docx \
		--account-key $$(grep AZURE_STORAGE_KEY .env | cut -d= -f2-)
	open proposal_output.docx

# ─── Knowledge Base ────────────────────────────────────────────────────────
inspect:
	python scripts/inspect_chunks.py

inspect-file:
	python scripts/inspect_chunks.py --file $(F)

duplicates:
	python scripts/inspect_chunks.py --duplicates

registry:
	python scripts/show_registry.py

# ─── Ingestion ─────────────────────────────────────────────────────────────
ingest:
	python -m src.ingest

ingest-file:
	python scripts/ingest_source.py --file $(F)

upload:
# Uploads new files from data/documents/ to blob storage.
	az storage blob upload-batch \
		--account-name ragdocuments1337 \
		--destination documents \
		--source data/documents \
		--account-key $$(grep AZURE_STORAGE_KEY .env | cut -d= -f2-) \
		--overwrite false \
		--pattern "*.docx" \
		--pattern "*.pdf" \
		--pattern "*.txt" \
		--pattern "*.md"

upload-file:
	az storage blob upload \
		--account-name $(STORAGE_ACCOUNT) \
		--container-name documents \
		--name $(F) \
		--file data/documents/$(F) \
		--account-key $(shell grep AZURE_STORAGE_KEY .env | cut -d= -f2-)

upload-rfp:
	az storage blob upload \
		--account-name ragdocuments1337 \
		--container-name documents \
		--name rfp-inputs/$(F) \
		--file data/rfp/$(F) \
		--account-key $$(grep AZURE_STORAGE_KEY .env | cut -d= -f2-)

publish:
#Upload + ingest in one command.
	az storage blob upload-batch \
		--account-name ragdocuments1337 \
		--destination documents \
		--source data/documents \
		--account-key $$(grep AZURE_STORAGE_KEY .env | cut -d= -f2-) \
		--overwrite false
	gh workflow run ingest.yml && gh run watch

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
#Triggers the ingest GitHub Actions workflow without uploading anything.
	gh workflow run ingest.yml && gh run watch

release:
	gh workflow run ingest.yml && gh run watch
	gh workflow run deploy.yml && gh run watch

# ─── Logs ──────────────────────────────────────────────────────────────────
logs:
	az containerapp logs show --name rag-api --resource-group rag-rg --follow --tail 50

logs-history:
	az containerapp logs show --name rag-api --resource-group rag-rg --tail 200 | grep "endpoint="

test:
	pytest tests/test_api.py -v -m "not slow"

test-full:
	pytest tests/test_api.py -v

test-local:
	API_URL=http://localhost:8000 pytest tests/test_api.py -v

# ─── Markup ──────────────────────────────────────────────────────────────────
lint:
	black src/ scripts/
	isort src/ scripts/
	flake8 --max-line-length=120 --extend-ignore=E203,W503,E402 src/ scripts/