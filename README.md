# Transcript Podcastify

A monorepo containing two integrated projects:
1. YouTube Transcripts - A Flask application that handles YouTube video transcript analysis
2. Podcastify - An open-source project for converting text into podcast-style audio content

## Project Structure

```
transcript_podcastify/              # Root directory
├── youtube_transcripts/            # YouTube transcripts analysis project
│   ├── app.py                     # Main Flask application
│   ├── scripts/
│   │   ├── podcast/              # Podcast integration module
│   │   └── ...
│   └── ...
├── podcastify/                    # To be added: Podcast generation service
├── docker-compose.yml             # Local development setup
├── .env.example                   # Shared environment variables
└── README.md                      # This file
```

## Getting Started

1. Clone the repository:
```bash
git clone https://github.com/yourusername/transcript_podcastify.git
cd transcript_podcastify
```

2. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. Start the services:
```bash
docker-compose up -d
```

4. Access the services:
- YouTube Transcripts: http://localhost:5003
- Podcastify: Coming soon

## Development

### Prerequisites
- Docker and Docker Compose
- Python 3.8+
- Git

### Local Development
1. Start the services in development mode:
```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

2. Install development dependencies:
```bash
cd youtube_transcripts
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Contributing

1. Create a new branch for your feature
2. Make your changes
3. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 