FROM postgis/postgis:15-3.3

RUN echo 'Acquire::ForceIPv4 "true";' > /etc/apt/apt.conf.d/99force-ipv4 \
    && if [ -f /etc/apt/sources.list.d/pgdg.list ]; then sed -i 's|http://apt.postgresql.org/pub/repos/apt|http://mirrors.aliyun.com/postgresql/repos/apt|g' /etc/apt/sources.list.d/pgdg.list; fi \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
       postgresql-15-pgvector \
    && rm -rf /var/lib/apt/lists/*
