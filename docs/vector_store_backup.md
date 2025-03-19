# Vector Store Backup Strategy

This document outlines the backup strategy for the ChromaDB vector store used in the YouTube Transcript Analyzer.

## Backup Approaches

The application implements two complementary backup strategies:

1. **Filesystem Backup**: 
   - Direct copy of the ChromaDB directory structure
   - Preserves all data, including metadata and embeddings
   - Fast and reliable for local deployments
   - Ideal for quick restoration

2. **API Export**:
   - Uses ChromaDB Data Pipes to export collections via the API
   - Creates portable backups in JSON format
   - Useful for migration between environments
   - More resilient to internal database format changes

## Backup Schedule

- **Weekly automatic backups** are configured to run every Sunday at midnight
- Additional automatic backups can be scheduled using cron or other task schedulers
- Manual backups can be triggered using the provided script or via the web interface
- A maximum of 5 backups are retained by default (configurable)

## Backup Location

By default, backups are stored on the external drive at `/Volumes/RileyNumber1/youtube_transcription/chroma_db_backup` with timestamped subdirectories:
```
/Volumes/RileyNumber1/youtube_transcription/chroma_db_backup/
├── chroma_backup_20250311_120000/
│   ├── chroma_db/           # Filesystem backup
│   └── chroma_export/       # API export (if enabled)
├── chroma_backup_20250310_120000/
└── ...
```

### Changing the Backup Location

You can specify a different backup location if needed:

```bash
# Different external drive
python backup/backup_vector_store.py --source chroma_db --backup-dir /Volumes/OtherDrive/backups

# Local directory
python backup/backup_vector_store.py --source chroma_db --backup-dir ./backups
```

When using the API endpoint, you can specify a different backup location in the request body:

```json
{
  "backup_dir": "/Volumes/OtherDrive/backups",
  "api_export": true,
  "max_backups": 10
}
```

## Restoration Process

### Filesystem Restore

1. Stop the application
2. Rename or remove the current `chroma_db` directory
3. Copy the backup `chroma_db` directory to the application root
4. Restart the application

### API Import Restore

1. Install ChromaDB Data Pipes: `pip install chromadb-data-pipes`
2. Run the import command:
   ```
   python -m chromadb_data_pipes import \
     --source file://path/to/backup/chroma_export \
     --destination chroma://path/to/new/chroma_db \
     --format json
   ```
3. Restart the application

## Manual Backup

To manually trigger a backup, use the backup script:

```bash
# Basic filesystem backup (uses default external drive location)
python backup/backup_vector_store.py

# With API export (requires chromadb-data-pipes)
python backup/backup_vector_store.py --api-export

# Custom backup retention
python backup/backup_vector_store.py --max-backups 10
```

## Setting Up Scheduled Backups

### On Linux/macOS (using cron)

The application includes a helper script to set up weekly backups:

```bash
# Run the setup script to configure weekly backups
./backup/setup_backup_cron.sh
```

This will set up a cron job to run backups every Sunday at midnight.

To manually configure or modify the schedule:

1. Open your crontab file:
   ```bash
   crontab -e
   ```

2. Add or modify the line for the backup schedule:
   ```
   # Run backup every Sunday at midnight
   0 0 * * 0 cd /path/to/youtube_transcripts && python backup/backup_vector_store.py --api-export
   
   # Alternative: Run backup every day at 2 AM
   # 0 2 * * * cd /path/to/youtube_transcripts && python backup/backup_vector_store.py
   ```

### On Windows (using Task Scheduler)

1. Open Task Scheduler
2. Create a new Basic Task
3. Set the trigger to Daily
4. Set the action to Start a Program
5. Program/script: `python`
6. Arguments: `backup/backup_vector_store.py`
7. Start in: `C:\path\to\youtube_transcripts`

## Dependencies

To use the API export functionality, install the ChromaDB Data Pipes package:

```bash
pip install chromadb-data-pipes
``` 