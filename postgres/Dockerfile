FROM postgres:17.4

# Copy the initialization SQL script into the Docker image
COPY ./init/init.sql /docker-entrypoint-initdb.d/

EXPOSE 5432