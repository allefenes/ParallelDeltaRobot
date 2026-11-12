# Kenarın (Pi delta_edge ya da sanal Pi) telemetrisi.
builtin_interfaces/Time stamp
# state: IDLE, RUNNING, HOLD, FAULT, TORQUE_OFF
string state
# Motor açıları, radyan (motor_1..3).
float64[3] angles
# Servo sıcaklıkları, °C.
float64[3] temps
# Servo yükleri, nominal torkun oranı (-1..1).
float64[3] loads
# Servo gerilimleri, V.
float64[3] voltages
# Oynatılan yörünge ve örnek sırası (boşta: son yörünge, -1).
string trajectory_id
int32 index
