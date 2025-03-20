#!/bin/bash

# Start Ollama in the background
/bin/ollama serve &
pid=$!

# Wait for Ollama to start
sleep 5

echo "🔄 Pulling Mistral model..."
ollama pull mistral
echo "✅ Model pulled successfully!"

# Wait for the Ollama process
wait $pid 