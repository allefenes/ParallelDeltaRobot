# 1. kapının (sunucu süpervizörü) her karar için yayımladığı olay.
builtin_interfaces/Time stamp
string trajectory_id
bool accepted
# requirement: ilgili güvenlik gereksinimi (docs/guvenlik-gereksinimleri.md): "G1", "G2", "G3",
#              "G4", "G5"; kenar meşgulse "DURUM"; kabulde boş.
string requirement
string reason
# Reddedilen örneğin sırası (0'dan); yörünge düzeyi ya da kabulse -1.
int32 sample_index
# Hedef P, robot çerçevesinde, mm.
geometry_msgs/Point target_mm
