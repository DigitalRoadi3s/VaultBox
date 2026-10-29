FROM python:3.12-alpine
# Site only. The paid STL files are NOT in the image: mount them at /app/parts (read-only).
WORKDIR /app
COPY index.html app.js style.css ./
COPY data ./data
COPY assets ./assets
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh && adduser -D -u 10001 vault
USER vault
EXPOSE 8765
HEALTHCHECK --interval=30s --timeout=3s CMD wget -qO- http://127.0.0.1:8765/data/catalog.json >/dev/null || exit 1
ENTRYPOINT ["docker-entrypoint.sh"]
