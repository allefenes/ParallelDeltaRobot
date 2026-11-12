// `fault` mesajının `code` değerleri. Sunucu bunlara göre karar verir; metinler sabittir.
#pragma once

namespace delta_edge::fault {

inline constexpr char kParseError[] = "parse_error";                // G4: bozuk/katı olmayan mesaj
inline constexpr char kJointLimit[] = "joint_limit";                // G1
inline constexpr char kNonFinite[] = "non_finite";                  // G4
inline constexpr char kVelocity[] = "velocity_limit";               // G5
inline constexpr char kAccel[] = "accel_limit";                     // G5
inline constexpr char kPeriod[] = "bad_period";                     // period_ms aralık dışı
inline constexpr char kEmpty[] = "empty_trajectory";                // nokta yok
inline constexpr char kTooManyPoints[] = "too_many_points";         // kMaxPoints aşıldı
inline constexpr char kOverTemp[] = "over_temperature";             // G9
inline constexpr char kOverLoad[] = "over_load";                    // G9
inline constexpr char kVoltage[] = "voltage";                       // G9
inline constexpr char kDriver[] = "driver";                         // sürücü okunamadı
inline constexpr char kHeartbeatHold[] = "heartbeat_hold";          // G6: T_stop aşıldı
inline constexpr char kHeartbeatOff[] = "heartbeat_torque_off";     // G7: T_off aşıldı
inline constexpr char kHeartbeatRequired[] = "heartbeat_required";  // taze kalp atışı yok
inline constexpr char kNotReady[] = "not_ready";                    // bu durumda kabul edilmez
inline constexpr char kEstop[] = "estop";                           // fiziksel acil stop girişi

}  // namespace delta_edge::fault
