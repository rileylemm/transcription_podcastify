from vector_db.vector_store import VectorStore

# Initialize vector store
vector_store = VectorStore(persist_directory="chroma_db")

# Query the Reddit collection directly
results = vector_store.reddit_collection.query(
    query_texts=[""],  # Empty query to match all documents
    where={"$and": [
        {"content_type": {"$eq": "reddit_post"}},
        {"segment_index": {"$eq": 0}}
    ]},
    n_results=10000
)

print(f"\nQuerying Reddit collection directly:")
if results["ids"][0]:
    for i, (doc_id, metadata) in enumerate(zip(results["ids"][0], results["metadatas"][0])):
        print(f"\nDocument {i+1}:")
        print(f"ID: {doc_id}")
        print("Metadata:", metadata)
        print("-" * 50)
else:
    print("No documents found in Reddit collection") 