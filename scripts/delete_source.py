# scripts/delete_source.py
import os
import sys
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
from qdrant_client.models import PayloadSchemaType

load_dotenv()

client = QdrantClient(
    url=os.getenv("QDRANT_URL"),
    api_key=os.getenv("QDRANT_API_KEY")
)

source = sys.argv[1]  # filename to delete

client.create_payload_index(
    collection_name="rag_docs",
    field_name="filename",
    field_schema=PayloadSchemaType.KEYWORD
)

result = client.delete(
    collection_name="rag_docs",
    points_selector=Filter(
        must=[FieldCondition(
            key="filename",
            match=MatchValue(value=source)
        )]
    )
)

print(f"Deleted all chunks with filename: {source}")
print(f"Result: {result}")
