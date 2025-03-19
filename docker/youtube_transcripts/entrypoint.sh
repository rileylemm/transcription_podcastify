#!/bin/bash
set -e

# Wait for any external services if needed (can be uncommented later)
# until nc -z $DB_HOST $DB_PORT; do
#     echo "Waiting for database to be ready..."
#     sleep 2
# done

# Start the Flask application
exec flask run --host=0.0.0.0 --port=5004 