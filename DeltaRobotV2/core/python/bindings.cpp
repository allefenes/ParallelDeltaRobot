// delta_core Python bağlaması (pybind11). Python istemcisi, datasheet ve testler kullanır.
// Vektörler ve açılar Python'da 3 elemanlı tuple olarak geçer (mm, derece).
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include "delta_core/kinematics.hpp"
#include "delta_core/version.hpp"

namespace py = pybind11;
using delta_core::Angles;
using delta_core::DeltaKinematics;
using delta_core::DeltaParams;
using delta_core::Vec3;

namespace {
using Tuple3 = std::array<double, 3>;
Vec3 to_vec(const Tuple3& t) { return {t[0], t[1], t[2]}; }
Tuple3 from_vec(const Vec3& v) { return {v.x, v.y, v.z}; }
}  // namespace

PYBIND11_MODULE(delta_core_py, m) {
  m.doc() = "Delta Robotics V2 kinematik çekirdeği (mm, derece; +Z yukarı)";
  m.attr("__version__") = delta_core::kVersion;

  py::class_<DeltaParams>(m, "DeltaParams")
      .def(py::init<>())
      .def_readwrite("base_radius", &DeltaParams::base_radius)
      .def_readwrite("bicep_length", &DeltaParams::bicep_length)
      .def_readwrite("forearm_length", &DeltaParams::forearm_length)
      .def_readwrite("platform_radius", &DeltaParams::platform_radius)
      .def_readwrite("ee_offset", &DeltaParams::ee_offset)
      .def_readwrite("base_to_floor", &DeltaParams::base_to_floor)
      .def_readwrite("arm_angles", &DeltaParams::arm_angles)
      .def_readwrite("motor_limit_min", &DeltaParams::motor_limit_min)
      .def_readwrite("motor_limit_max", &DeltaParams::motor_limit_max)
      .def_readwrite("spherical_joint_limit", &DeltaParams::spherical_joint_limit)
      .def_readwrite("motor_step", &DeltaParams::motor_step);

  m.def("load_params", &delta_core::load_params, py::arg("yaml_path"),
        "config/robot.yaml'dan parametreleri okur");

  py::class_<DeltaKinematics>(m, "DeltaKinematics")
      .def(py::init<DeltaParams>(), py::arg("params"))
      .def_property_readonly("params", &DeltaKinematics::params)
      .def(
          "inverse",
          [](const DeltaKinematics& k, const Tuple3& p) -> std::optional<Angles> {
            return k.inverse(to_vec(p));
          },
          py::arg("P"), "P (mm) -> θ (derece) ya da None")
      .def(
          "forward",
          [](const DeltaKinematics& k, const Angles& th) -> std::optional<Tuple3> {
            const auto p = k.forward(th);
            if (!p) return std::nullopt;
            return from_vec(*p);
          },
          py::arg("theta"), "θ (derece) -> P (mm) ya da None")
      .def("jacobian", &DeltaKinematics::jacobian, py::arg("theta"),
           "dP/dθ (mm/rad), satır = P bileşeni; tekilse None")
      .def("condition_number", &DeltaKinematics::condition_number, py::arg("theta"))
      .def(
          "rod_tilt_deg",
          [](const DeltaKinematics& k, int i, double th, const Tuple3& p) {
            return k.rod_tilt_deg(i, th, to_vec(p));
          },
          py::arg("arm"), py::arg("theta"), py::arg("P"))
      .def(
          "check_point",
          [](const DeltaKinematics& k, const Tuple3& p) {
            const auto r = k.check_point(to_vec(p));
            return py::make_tuple(r.ok, r.arm, r.reason);
          },
          py::arg("P"), "(ok, kol, neden)")
      .def(
          "check_limits",
          [](const DeltaKinematics& k, const Angles& th, const Tuple3& p) {
            const auto r = k.check_limits(th, to_vec(p));
            return py::make_tuple(r.ok, r.arm, r.reason);
          },
          py::arg("theta"), py::arg("P"), "(ok, kol, neden)")
      .def(
          "elbow",
          [](const DeltaKinematics& k, int i, double th) { return from_vec(k.elbow(i, th)); },
          py::arg("arm"), py::arg("theta"));
}
