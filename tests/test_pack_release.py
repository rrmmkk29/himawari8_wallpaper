import importlib.util
from pathlib import Path


def load_pack_release_module():
    repo_root = Path(__file__).resolve().parents[1]
    module_path = repo_root / "scripts" / "pack_release.py"
    spec = importlib.util.spec_from_file_location("pack_release", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_build_output_path_uses_project_name_and_label() -> None:
    module = load_pack_release_module()
    output = module.build_output_path(
        Path("release"),
        "himawari-dynamic-wallpaper",
        "0.1.0",
        "v0.1.1",
    )

    assert output == Path("release") / "himawari-dynamic-wallpaper-v0.1.1.zip"


def test_should_skip_filters_local_runtime_files() -> None:
    module = load_pack_release_module()

    assert module.should_skip(Path("config.json")) is True
    assert module.should_skip(Path("wallpaper_001.png")) is True
    assert module.should_skip(Path("origin_wallpaper_001.png")) is True
    assert module.should_skip(Path("src") / "himawari_wallpaper" / "app.py") is False
