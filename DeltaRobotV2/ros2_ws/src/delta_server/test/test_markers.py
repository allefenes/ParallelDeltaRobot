"""markers modülü: ret yazısı RViz'de okunur olmalı (ASCII, boşluk yerine sekme, iki satır)."""

from delta_server import markers
from visualization_msgs.msg import Marker

REASON = "G2: rot başı açı limiti (hedef yol, kol 2, örnek 73)"


def test_reject_label_two_lines():
    assert markers.reject_label(REASON) == (
        "RET G2: rot başı açı limiti\n(hedef yol, kol 2, örnek 73)"
    )
    assert markers.reject_label("G4: boş yörünge") == "RET G4: boş yörünge"


def test_rviz_text_is_ascii_without_spaces():
    t = markers.rviz_text(markers.reject_label(REASON))
    assert t.isascii() and " " not in t
    assert t.split("\n")[0].split("\t") == ["RET", "G2:", "rot", "basi", "aci", "limiti"]
    assert markers.rviz_text("300°/s²") == "300\tdeg/s^2"


def test_target_markers_reject_and_accept():
    sphere, label, leader = markers.target_markers((60.0, 0.0, -155.0), False, REASON)
    assert label.type == Marker.TEXT_VIEW_FACING and label.action == Marker.ADD
    assert "G2:" in label.text and label.text.isascii()
    # Yazı robotun üstünde, çizgi yazıdan hedefe iner
    assert label.pose.position.z * 1000.0 == markers.LABEL_Z_MM
    assert leader.type == Marker.LINE_LIST and len(leader.points) == 2
    assert abs(leader.points[1].z * 1000.0 + 155.0) < 1e-9
    assert abs(sphere.pose.position.x - 0.060) < 1e-12

    _, label, leader = markers.target_markers((0.0, 0.0, -200.0), True, "kabul")
    assert label.action == Marker.DELETE and leader.action == Marker.DELETE
