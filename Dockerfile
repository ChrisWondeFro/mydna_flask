FROM python:3.12-slim AS build

WORKDIR /build
COPY pyproject.toml README.md LICENSE ./
COPY mydna ./mydna

RUN python -m venv /opt/venv \
 && /opt/venv/bin/pip install --no-cache-dir --upgrade pip \
 && /opt/venv/bin/pip install --no-cache-dir .


FROM python:3.12-slim

# Run as an unprivileged user. The previous image ran everything as root.
RUN useradd --create-home --uid 10001 mydna

COPY --from=build /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MATPLOTLIBRC=/tmp \
    MPLCONFIGDIR=/tmp/matplotlib \
    MYDNA_HOST=0.0.0.0 \
    MYDNA_PORT=8000 \
    MYDNA_INDEX_PATH=/data/clinvar.sqlite

# The index is large and rebuilt independently of the image, so mount it:
#   docker run -v "$PWD/data:/data" -p 8000:8000 mydna
VOLUME ["/data"]

USER mydna
WORKDIR /home/mydna

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=4).status==200 else 1)"

# NOTE: this image serves an unauthenticated endpoint that accepts genetic
# data. Bind it to a private interface. See SECURITY.md.
CMD ["mydna", "serve"]
