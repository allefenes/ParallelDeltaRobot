# Delta Robotics V2 sunucu ROS2 (Jazzy) imajı: 1. güvenlik kapısı (süpervizör), yörünge planlayıcı,
# durum yayıncısı (dijital ikiz TF'i), RViz ve testler.
#
# Derleme bağlamı depo köküdür (DeltaRobotV2/):
#   docker build -f docker/ros/Dockerfile -t deltarobotv2-ros:latest .
# /opt/delta, depo düzeninin kopyasıdır (core/, config/, cad/out/meshes/, ros2_ws/src/); böylece
# paketler depodaki göreli yollarla (ör. ../../../cad/out/meshes) hem imajda hem bağlı
# çalışma alanında aynı şekilde derlenir.
FROM deltarobotv2-dev:latest AS base

USER root
ENV DEBIAN_FRONTEND=noninteractive

# ROS paketleri: RViz, robot_state_publisher, xacro, tf2, launch_testing.
# Sistem: başsız ekran (Xvfb), ekran görüntüsü (ImageMagick), ROS grafiği (graphviz),
# yazılım OpenGL (mesa), kenar köprüsü için websockets.
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-colcon-common-extensions \
        ros-jazzy-rosidl-default-generators \
        ros-jazzy-rviz2 \
        ros-jazzy-robot-state-publisher \
        ros-jazzy-xacro \
        ros-jazzy-tf2-ros \
        ros-jazzy-tf2-tools \
        ros-jazzy-tf-transformations \
        ros-jazzy-launch-testing \
        ros-jazzy-launch-testing-ament-cmake \
        ros-jazzy-launch-testing-ros \
        ros-jazzy-rclpy \
        ros-jazzy-trajectory-msgs \
        ros-jazzy-visualization-msgs \
        ros-jazzy-geometry-msgs \
        ros-jazzy-sensor-msgs \
        xvfb \
        x11-utils \
        imagemagick \
        graphviz \
        python3-websockets \
        mesa-utils \
        libgl1-mesa-dri \
    && rm -rf /var/lib/apt/lists/*

# Kinematik çekirdeği (delta_core) ve Python modülü (delta_core_py). Testler dev imajında/CI'da
# koşar; burada yalnız modül derlenir ve sistem Python yoluna kurulur.
COPY core /opt/delta/core
COPY config /opt/delta/config
RUN cmake -S /opt/delta/core -B /tmp/delta_core -G Ninja -DCMAKE_BUILD_TYPE=Release \
        -DDELTA_CORE_BUILD_TESTS=OFF \
    && cmake --build /tmp/delta_core \
    && install -m 644 /tmp/delta_core/delta_core_py*.so /usr/local/lib/python3.12/dist-packages/ \
    && rm -rf /tmp/delta_core \
    && python3 -c "import delta_core_py as dc; print('delta_core_py', dc.__version__)"

ENV DELTA_ROBOT_YAML=/opt/delta/config/robot.yaml \
    LIBGL_ALWAYS_SOFTWARE=1 \
    PYTHONDONTWRITEBYTECODE=1

FROM base AS ros

# CAD mesh'leri (bağ başına STL, bağın yerel çerçevesinde) ve ROS2 çalışma alanı.
COPY cad/out/meshes /opt/delta/cad/out/meshes
COPY cad/out/mass_properties.json /opt/delta/cad/out/mass_properties.json
COPY ros2_ws/src /opt/delta/ros2_ws/src
RUN . /opt/ros/jazzy/setup.sh \
    && cd /opt/delta/ros2_ws \
    && colcon build --event-handlers console_direct- \
    && rm -rf build log

COPY docker/ros/entrypoint.sh /usr/local/bin/delta-entrypoint
RUN chmod 755 /usr/local/bin/delta-entrypoint \
    && echo "source /opt/delta/ros2_ws/install/setup.bash" >> /home/ubuntu/.bashrc

USER ubuntu
WORKDIR /workspace
ENTRYPOINT ["/usr/local/bin/delta-entrypoint"]
CMD ["bash"]
