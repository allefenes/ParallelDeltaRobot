# Sandbox koşucusu (api.md, Koşucu ↔ API): asyncio + websockets sunucusu ve docker CLI.
# Derleme bağlamı DeltaRobotV2/:
#   docker build -f docker/runner/Dockerfile -t deltarobotv2-runner .              (servis)
#   docker build -f docker/runner/Dockerfile --target test -t deltarobotv2-runner:test .
# Koşucu Docker soketini tutar (ana makinede root eşdeğeri); yalnız iç ağda çalışır, bkz. sandbox/README.md.
ARG DOCKER_CLI_IMAGE=docker:27.3.1-cli

FROM ${DOCKER_CLI_IMAGE} AS dockercli

FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
# Resmî imajdaki statik docker istemcisi; sunucuyla API sürümünü kendisi uzlaşır.
COPY --from=dockercli /usr/local/bin/docker /usr/local/bin/docker
ARG WEBSOCKETS_VERSION=13.1
RUN pip install "websockets==${WEBSOCKETS_VERSION}"

# Testler: kaynak çalışma ağacından salt okunur bağlanır (sandbox/run_tests.sh).
FROM base AS test
ARG PYTEST_VERSION=8.3.3
RUN pip install "pytest==${PYTEST_VERSION}"

FROM base AS runtime
COPY sandbox/runner/delta_runner /app/delta_runner
WORKDIR /app
EXPOSE 8100
# Soket erişimi için root (soket grubu ana makineye göre değişir); kullanıcı kodu bu süreçte çalışmaz.
CMD ["python", "-m", "delta_runner"]
