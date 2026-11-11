# Delta Robotics V2 geliştirme imajı
# Ubuntu 24.04 (noble) + ROS2 Jazzy + C++/Python araçları
FROM ros:jazzy-ros-base

ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        cmake \
        ninja-build \
        libgtest-dev \
        clang-format \
        python3-pytest \
        python3-yaml \
        python3-numpy \
    && rm -rf /var/lib/apt/lists/*

# ubuntu kullanıcısı (UID 1000) noble imajında hazır gelir
RUN echo "source /opt/ros/jazzy/setup.bash" >> /home/ubuntu/.bashrc

USER ubuntu
WORKDIR /workspace

CMD ["bash"]
