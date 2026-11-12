// Durum adları (telemetri `state` alanı).
#include "delta_edge/state.hpp"

namespace delta_edge {

const char* state_name(State s) {
  switch (s) {
    case State::kIdle:
      return "IDLE";
    case State::kRunning:
      return "RUNNING";
    case State::kHolding:
      return "HOLDING";
    case State::kFault:
      return "FAULT";
    case State::kTorqueOff:
      return "TORQUE_OFF";
    case State::kEstop:
      return "ESTOP";
  }
  return "UNKNOWN";
}

bool torque_enabled(State s) {
  return s == State::kIdle || s == State::kRunning || s == State::kHolding || s == State::kFault;
}

}  // namespace delta_edge
