FROM python:3.12-slim AS builder
WORKDIR /build
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_NO_CACHE_DIR=1
COPY pyproject.toml README.md ./
COPY src ./src
RUN python -m pip wheel --wheel-dir /wheels .

FROM python:3.12-slim
RUN useradd --create-home --uid 10001 generator
WORKDIR /app
COPY --from=builder /wheels /wheels
RUN python -m pip install --no-cache-dir /wheels/* && rm -rf /wheels
RUN mkdir /app/output && chown generator:generator /app/output
USER generator
ENTRYPOINT ["riskgen"]
CMD ["generate", "--output", "/app/output"]
