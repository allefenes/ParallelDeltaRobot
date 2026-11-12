# Komut API'si (F4): ROS2 imajı + FastAPI. Derleme bağlamı DeltaRobotV2/.
#   docker build -f docker/api/Dockerfile -t deltarobotv2-api:latest .
# Konteyner `server`ın ağ ad alanını paylaşır (compose: network_mode service:server); ROS2 trafiği
# localhost'ta kalır. Web arayüzü ve i18n kataloğu imaja kopyalanır; CAD mesh'leri ROS imajında.
FROM deltarobotv2-ros:latest

USER root
COPY api /opt/delta/api
RUN pip install --no-cache-dir --break-system-packages --root-user-action=ignore /opt/delta/api \
    && rm -rf /opt/delta/api/build
COPY web /opt/delta/web
COPY i18n/locales /opt/delta/i18n/locales

USER ubuntu
ENV DELTA_WEB_DIR=/opt/delta/web \
    DELTA_I18N_DIR=/opt/delta/i18n/locales \
    DELTA_MESHES_DIR=/opt/delta/cad/out/meshes \
    DELTA_ROBOT_YAML=/opt/delta/config/robot.yaml \
    PYTHONDONTWRITEBYTECODE=1
EXPOSE 8000
CMD ["python3", "-m", "delta_api.main"]
