# Sanal Pi: delta_edge kenar servisi + MockDriver. Gerçek Pi ile aynı ikili ve aynı protokol;
# sunucu karşısındakinin simülasyon mu gerçek robot mu olduğunu bilmez (mimari ilke 6).
# Derleme bağlamı DeltaRobotV2/:  docker build -f docker/edge/Dockerfile -t deltarobotv2-edge .
FROM deltarobotv2-dev:latest AS build
USER root
COPY edge /src/edge
COPY config /src/config
RUN cmake -S /src/edge -B /tmp/build -G Ninja -DCMAKE_BUILD_TYPE=Release \
        -DDELTA_EDGE_BUILD_TESTS=OFF \
    && cmake --build /tmp/build \
    && cmake --install /tmp/build --prefix /opt/delta_edge

FROM ubuntu:24.04
# Çalışma zamanı: yaml-cpp, OpenSSL, ağ arıza enjeksiyonu için iproute2 (tc netem, yalnız test)
RUN apt-get update && apt-get install -y --no-install-recommends \
        libyaml-cpp0.8 libssl3 ca-certificates iproute2 \
    && rm -rf /var/lib/apt/lists/*
COPY --from=build /opt/delta_edge/bin/delta_edge /usr/local/bin/delta_edge
COPY config/robot.yaml /etc/delta_edge/robot.yaml
COPY edge/config/edge.yaml /etc/delta_edge/edge.yaml
ENV DELTA_ROBOT_YAML=/etc/delta_edge/robot.yaml \
    DELTA_EDGE_YAML=/etc/delta_edge/edge.yaml \
    DELTA_DRIVER=mock
ENTRYPOINT ["/usr/local/bin/delta_edge"]
