serve:
	uvicorn src.api:app --reload --port 8000

ingest:
	python -m src.ingest

ask:
	python scripts/ask.py "$(Q)" --show-chunks --top-k 10

inspect:
	python scripts/inspect_chunks.py

inspect-file:
	python scripts/inspect_chunks.py --file $(F)

duplicates:
	python scripts/inspect_chunks.py --duplicates

debug:
	python scripts/debug_parse.py --file $(F)

delete:
	python scripts/delete_source.py $(F)

delete-all:
	python scripts/delete_source.py --all

ingest-file:
	python scripts/ingest_source.py --file $(F)

deploy:
	gh workflow run deploy.yml

sync:
	gh workflow run ingest.yml