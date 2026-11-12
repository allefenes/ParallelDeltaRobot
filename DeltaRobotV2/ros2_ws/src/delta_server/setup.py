"""delta_server paket tanımı (ament_python)."""

from glob import glob

from setuptools import find_packages, setup

PACKAGE = "delta_server"

setup(
    name=PACKAGE,
    version="0.1.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{PACKAGE}"]),
        (f"share/{PACKAGE}", ["package.xml"]),
        (f"share/{PACKAGE}/config", glob("config/*.yaml")),
        (f"share/{PACKAGE}/launch", glob("launch/*.py")),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="Delta Robotics",
    maintainer_email="dev@deltarobotics.local",
    description="Delta Robotics V2 sunucu düğümleri (1. güvenlik kapısı, planlayıcı, durum)",
    license="Proprietary",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "delta_state_publisher = delta_server.state_publisher_node:main",
            "trajectory_planner = delta_server.trajectory_planner_node:main",
            "supervisor = delta_server.supervisor_node:main",
            "sim_executor = delta_server.sim_executor_node:main",
        ],
    },
)
