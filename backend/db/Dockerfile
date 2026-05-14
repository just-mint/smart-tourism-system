FROM postgis/postgis:15-3.3

RUN apt-get update \
<<<<<<< Updated upstream
   && apt-cache search postgresql-15-pgvector \
   && apt-get install -y --no-install-recommends \
   postgresql-15-pgvector \
   && rm -rf /var/lib/apt/lists/*

# Auto-create extensions (postgis, vector, pg_trgm, uuid-ossp) on first boot
COPY init_db.sql /docker-entrypoint-initdb.d/10_init_extensions.sql
=======
    && apt-cache search postgresql-15-pgvector \
    && apt-get install -y --no-install-recommends \
       postgresql-15-pgvector \
    && rm -rf /var/lib/apt/lists/*

COPY init_db.sql /docker-entrypoint-initdb.d/init_db.sql
>>>>>>> Stashed changes
