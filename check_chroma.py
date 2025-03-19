import chromadb
from chromadb.config import Settings

# Initialize ChromaDB with the specific persistent directory
chroma_client = chromadb.PersistentClient(path="shared/data/chroma")

# Get all collections
collections = chroma_client.list_collections()
print("\nCollections found:", len(collections))

for collection_info in collections:
    collection = chroma_client.get_collection(name=collection_info)
    print(f"\nCollection: {collection_info}")
    print(f"Number of items: {collection.count()}")
    
    # Get all items from the collection
    results = collection.get()
    
    if results and len(results['ids']) > 0:
        print(f"\nFirst few items:")
        for i in range(min(3, len(results['ids']))):
            print(f"\nID: {results['ids'][i]}")
            if 'metadatas' in results and results['metadatas']:
                print(f"Metadata: {results['metadatas'][i]}")
            if 'documents' in results and results['documents']:
                print(f"Document preview: {results['documents'][i][:200]}...") 