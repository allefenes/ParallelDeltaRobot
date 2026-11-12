# Remote Acces Parallel Delta Robot Experiment Kit
![alt text](https://github.com/allefenes/ParallelDeltaRobot/blob/main/logo/logo.png)

## Delta Robotics V2 (on hold)

V2 is a from-scratch rewrite of the same robot. The server is the brain (ROS2 Jazzy, a C++ kinematics core, a two-layer safety gate, a digital twin, an API and a code sandbox). A thin but safe Raspberry Pi edge plays back time-stamped trajectories, enforces the final safety gate and a watchdog, and dials out to the server. All V2 work lives in [`DeltaRobotV2/`](DeltaRobotV2/); its documentation is in Turkish.

**Status (2026-11-12): on hold.** Phases F0–F4.5 and F6 are complete; the software half of F5 (AX-12A Dynamixel backend, servo setup tool, install and acceptance procedures) is done and the hardware half is suspended. The final deliverable is a single-page experience UI where the robot runs in simulation: in automatic mode it plays a sliding tic-tac-toe game by itself, and in manual mode you drive it with motor-angle sliders (forward kinematics) or XYZ targets (inverse kinematics); out-of-limit targets are rejected by the same safety gates.

| Automatic mode | Manual mode |
| --- | --- |
| ![Automatic mode](DeltaRobotV2/web/screenshots/otomatik.png) | ![Manual mode](DeltaRobotV2/web/screenshots/manuel.png) |

- **Run it:** with Docker Desktop, in `DeltaRobotV2/`: `docker compose --profile demo up -d --build`, then open https://localhost:8080 (local self-signed certificate).
- **Safety:** 14 requirements; G1–G10 and G14 proven by tests in every software layer; sandbox (G11) and the watchdog's software side (G13) tested; hardware-level checks suspended with F5.
- **Tests:** edge service 190 tests at 99% line coverage, mutation score 130/131 on safety-critical modules, ~175k fuzz inputs with no findings, end-to-end with fault injection 16/16, UI end-to-end (Playwright, against the real simulation) 11/11.
- **Datasheet:** [interactive datasheet](DeltaRobotV2/docs/datasheet/datasheet.html) (workspace, performance maps, ROS2 graph, scenario metrics).
- **Status and restart notes:** [DeltaRobotV2/README.md](DeltaRobotV2/README.md) and [DeltaRobotV2/docs/ilerleme.md](DeltaRobotV2/docs/ilerleme.md).

[![Built with Claude Code](https://img.shields.io/badge/Built%20with-Claude%20Code-D97757?logo=claude&logoColor=white)](https://claude.com/claude-code) V2 was developed with [Claude Code](https://claude.com/claude-code).

## V1 review and lessons carried into V2

V1 was a graduation project built solo alongside final-year coursework. Before starting V2, we reviewed the code end to end.

**Strengths**

- Correct forward and inverse kinematics: round-trip error ~1e-13 mm. Passive joint angles and the spherical-joint limit are computed as well.
- The code was refactored by hand from a single-file first version that had grown out of control (`LikeSoup/`) into a modular, object-oriented structure (`KilavuzDeltaRobotics/`); the kinematic model is independent of the UI.
- A working end-to-end pipeline: parametric robot definition → kinematics → trajectory validation and simulation → synchronized motor control and telemetry → image processing.
- Solid mechanics: output shafts are supported by bearings so the servos carry no arm loads, and with the motors unpowered the end effector moves freely by hand.

**To improve → how V2 addresses it**

- The motor command path could bypass the limit checks → in V2 every command passes through a single safety supervisor.
- Servo speed and command values were not limited → velocity/acceleration limits and value clamping in the supervisor.
- The serial port and the UI were used concurrently from several threads → a driver layer that is the sole owner of the hardware (ROS2).
- No tests, dependency list or packaging → C++ core with tests, Docker environment, CI.
- Build artifacts and large data were committed, and code style was inconsistent → `.gitignore`, automatic formatting and a pre-commit check.

## V1 (2024, archive)

The text below and the `LikeSoup/`, `KilavuzDeltaRobotics/`, `ImageProcessing/` and `WsAnalysis/` folders belong to the 2024 graduation project and are kept unchanged as a reference.

We are developing Remote Access Parallel Delta Robot Experiment Kit for TEKNOFEST competition. Our team name is DELTA ROBOTICS.

Our project consists of several different areas. These are listed below under the electronic, mechanical and software categories.

<h1>⚡  Electronics:</h1>

We use dynamixel AX12-A smart servos of the robotis brand. We control the entire system with Raspberry pi 4b (8GB). For this case, we fulfill the electronic requirements for communication by using the circuit below.


<h1>⚙️  Mechanics:</h1>

We have a small-sized delta robot design and we are constantly updating our designs as a result of the current tests.


<h1>💻 Softwares:</h1>

We are using raspbian-os on raspberry pi. Since we are in the prototype stage, we use Real-VNC with remote desktop access. We are developing an interface with the tkinter library in Python language. In the following stages, the project will be completely dockerized and the repository will be updated.
