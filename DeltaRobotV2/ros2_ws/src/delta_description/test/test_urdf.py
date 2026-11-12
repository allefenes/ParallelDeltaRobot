"""URDF testleri: xacro çıktısı geçerli, 11 bağ, 10 floating eklem, tüm mesh dosyaları kurulu."""

from __future__ import annotations

import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

from ament_index_python.packages import get_package_share_directory

MOVING = [
    "bicep_1",
    "bicep_2",
    "bicep_3",
    "forearm_1_a",
    "forearm_1_b",
    "forearm_2_a",
    "forearm_2_b",
    "forearm_3_a",
    "forearm_3_b",
    "platform",
]


def urdf() -> ET.Element:
    share = Path(get_package_share_directory("delta_description"))
    xml = subprocess.run(
        ["xacro", str(share / "urdf" / "delta.urdf.xacro")],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return ET.fromstring(xml)


def test_links_and_floating_joints():
    root = urdf()
    links = {link.get("name") for link in root.findall("link")}
    assert links == {"base_link", *MOVING}
    joints = root.findall("joint")
    assert len(joints) == len(MOVING)
    for j in joints:
        assert j.get("type") == "floating"
        assert j.find("parent").get("link") == "base_link"


def test_meshes_exist_and_colored():
    share = Path(get_package_share_directory("delta_description"))
    root = urdf()
    colors = {m.get("name") for m in root.findall("material")}
    assert {"aluminium", "pla", "steel", "motor", "pom", "magnet"} <= colors
    for link in root.findall("link"):
        visuals = link.findall("visual")
        assert visuals, link.get("name")
        for v in visuals:
            mesh = v.find("geometry/mesh")
            assert mesh.get("scale") == "0.001 0.001 0.001"
            rel = mesh.get("filename").replace("package://delta_description/", "")
            assert (share / rel).stat().st_size > 84
        assert float(link.find("inertial/mass").get("value")) > 0
