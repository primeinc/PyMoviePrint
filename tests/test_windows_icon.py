"""Validate the generated ICO contains real images for Explorer DPI variants."""
from pathlib import Path
import importlib.util
import struct
import pytest
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'windows' / 'build_icon.py'
SPEC = importlib.util.spec_from_file_location('pymovieprint_icon_builder', SCRIPT)
ICON_MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ICON_MODULE)


def test_multi_size_ico_roundtrip_from_committed_logo(tmp_path):
    source = ROOT / 'windows' / 'PyMoviePrint-icon.png'
    output = tmp_path / 'PyMoviePrint.ico'
    assert ICON_MODULE.build(source, output) == tuple(sorted(ICON_MODULE.SIZES))
    data = output.read_bytes()
    _, resource_type, count = struct.unpack_from('<HHH', data)
    assert resource_type == 1 and count == 9
    for size in ICON_MODULE.SIZES:
        with Image.open(output) as icon:
            icon.size = (size, size)
            icon.load()
            assert icon.size == (size, size)


def test_invalid_non_square_source_is_rejected(tmp_path):
    bad = tmp_path / 'non-square.png'
    Image.new('RGB', (256, 192), (8, 8, 32)).save(bad)
    with pytest.raises(ValueError, match='square'):
        ICON_MODULE.build(bad, tmp_path / 'bad.ico')


def test_real_logo_asset_has_expected_identity():
    import hashlib
    source = ROOT / 'windows' / 'PyMoviePrint-icon.png'
    assert source.is_file()
    assert hashlib.sha256(source.read_bytes()).hexdigest() == (
        '6794190d07898c9b0db8ebc9f8f071872c97cad4dfc31e9027753cdb3a165bb0'
    )


def test_registry_installer_and_executable_reuse_same_icon():
    iss = (ROOT / 'windows' / 'PyMoviePrint.iss').read_text('utf-8')
    spec = (ROOT / 'windows' / 'PyMoviePrint.spec').read_text('utf-8')
    workflow = (ROOT / '.github' / 'workflows' / 'windows-installer.yml').read_text('utf-8')
    smoke = (ROOT / 'windows' / 'smoke-install.ps1').read_text('utf-8')
    assert 'SetupIconFile=PyMoviePrint.ico' in iss
    assert 'Source: "PyMoviePrint.ico"; DestDir: "{app}"' in iss
    assert iss.count('ValueName: "Icon"; ValueData: "{app}\\PyMoviePrint.ico"') == 6
    assert "'windows', 'PyMoviePrint.ico'" in spec
    assert '      - name: Generate branded Windows icon' in workflow
    assert 'run: python windows/build_icon.py' in workflow
    assert "GetValue('Icon')" in smoke
    assert "DeleteValue('Icon', $false)" in smoke
    assert "Installer overwrote foreign Explorer Icon value" in smoke
