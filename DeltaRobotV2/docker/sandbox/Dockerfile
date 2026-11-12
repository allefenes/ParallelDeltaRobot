# Kullanıcı kodu konteyneri (api.md, Sandbox): python:3.12-slim + delta_robot istemcisi + bootstrap.
# Derleme bağlamı DeltaRobotV2/:  docker build -f docker/sandbox/Dockerfile -t deltarobotv2-sandbox .
# Kısıtlar imajda değil, koşucunun docker run bayraklarındadır (ağsız, salt okunur, kaynak sınırlı).
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# İstemci ve bağımlılıkları (httpx, websockets) dışında paket yok; pip de sonra kaldırılır.
COPY client /opt/src/client
RUN pip install /opt/src/client \
    && rm -rf /opt/src \
    && pip uninstall -y pip

COPY sandbox/bootstrap.py /opt/sandbox/bootstrap.py

# Derinlemesine savunma: setuid/setgid bitleri silinir (no-new-privileges zaten etkisiz kılar).
RUN find / -xdev -type f -perm /6000 -exec chmod a-s {} +

# nobody:nogroup; koşucu --user 65534:65534 ile de zorlar.
USER 65534:65534
WORKDIR /tmp
# -I: PYTHON* ortamı ve çalışma dizini yok sayılır; -u: tamponsuz (RPC satırları hemen çıkar); -B: .pyc yok.
ENTRYPOINT ["python", "-I", "-u", "-B", "/opt/sandbox/bootstrap.py"]
