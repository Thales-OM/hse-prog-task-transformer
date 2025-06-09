docker run --rm -v hse-prog-task-transformer_postgres_data:/target -v .:/backup alpine tar xzvf /backup/postgres_data_backup_20250521_180005.tar.gz -C /target
