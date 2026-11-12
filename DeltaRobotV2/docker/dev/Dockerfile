# Delta Robotics V2 geliştirme imajı.
# Taban: Ubuntu 24.04 (noble) + ROS2 Jazzy. Üstüne C++/Python derleme, test ve biçimlendirme araçları.
# Araç sürümleri sabitlenir; böylece yerelde, CI'da ve başka makinede aynı biçimlendirme çıkar.
FROM ros:jazzy-ros-base

ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8

# Derleme ve test: CMake + Ninja + GoogleTest (C++), pytest (Python).
# Biçimlendirme: clang-format (C++), Node.js (Prettier için).
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        cmake \
        ninja-build \
        libgtest-dev \
        clang-format \
        python3-pip \
        python3-pytest \
        python3-yaml \
        python3-numpy \
        python3-dev \
        pybind11-dev \
        python3-pybind11 \
        libyaml-cpp-dev \
        gcovr \
        libboost-dev \
        libssl-dev \
        nlohmann-json3-dev \
        clang \
        libclang-rt-18-dev \
        nodejs \
        npm \
    && rm -rf /var/lib/apt/lists/*

# Prettier: JSON, YAML, Markdown. Ruff: Python biçimlendirme (black stili) ve lint.
# Konteyner tek amaçlı olduğu için pip'in sistem paketi korumasını bilerek aşıyoruz.
ARG PRETTIER_VERSION=3.3.3
ARG RUFF_VERSION=0.6.9
# Testler: Hypothesis (özellik tabanlı testler), pytest-cov (kapsama ölçümü)
ARG HYPOTHESIS_VERSION=6.112.2
ARG PYTEST_COV_VERSION=5.0.0
# Datasheet: Plotly (etkileşimli grafikler; tarayıcıda sabit sürümlü plotly.js kullanılır)
ARG PLOTLY_VERSION=5.24.1
RUN npm install -g "prettier@${PRETTIER_VERSION}" \
    && pip3 install --no-cache-dir --break-system-packages \
        "ruff==${RUFF_VERSION}" \
        "hypothesis==${HYPOTHESIS_VERSION}" \
        "pytest-cov==${PYTEST_COV_VERSION}" \
        "plotly==${PLOTLY_VERSION}"

# ubuntu kullanıcısı (UID 1000) noble imajında hazır gelir; ROS ortamı kabukta otomatik yüklenir.
RUN echo "source /opt/ros/jazzy/setup.bash" >> /home/ubuntu/.bashrc

USER ubuntu
WORKDIR /workspace

CMD ["bash"]
