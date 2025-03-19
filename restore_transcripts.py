import chromadb
import json
import os
from collections import defaultdict

# Initialize ChromaDB client
chroma_client = chromadb.PersistentClient(path="shared/data/chroma")

# Create transcripts directory
os.makedirs("shared/data/transcripts", exist_ok=True)

# Get the collections
collections = chroma_client.list_collections()

# Process each collection
for collection_name in collections:
    collection = chroma_client.get_collection(name=collection_name)
    results = collection.get()
    
    # Group segments by video_id
    video_segments = defaultdict(list)
    
    for i in range(len(results['ids'])):
        metadata = results['metadatas'][i]
        document = results['documents'][i]
        video_id = metadata['video_id']
        
        segment = {
            'text': document,
            'start': metadata['start'],
            'duration': metadata['duration'],
            'segment_index': metadata['segment_index']
        }
        video_segments[video_id].append(segment)
    
    # Save each video's transcript
    for video_id, segments in video_segments.items():
        # Sort segments by index
        sorted_segments = sorted(segments, key=lambda x: x['segment_index'])
        
        # Create transcript data structure
        transcript_data = {
            'video_id': video_id,
            'segments': sorted_segments
        }
        
        # Save to file
        output_path = os.path.join('shared/data/transcripts', f'{video_id}.json')
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(transcript_data, f, indent=2, ensure_ascii=False)
        
        print(f"Restored transcript for video: {video_id}")

print("\nTranscript restoration complete!") 