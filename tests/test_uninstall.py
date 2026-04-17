from pathlib import Path

from himawari_wallpaper import uninstall


def test_collect_output_cleanup_paths_finds_known_runtime_files(tmp_path: Path) -> None:
    (tmp_path / "wallpaper_001.png").write_bytes(b"x")
    (tmp_path / "origin_wallpaper_001.png").write_bytes(b"x")
    (tmp_path / "note.txt").write_text("keep", encoding="utf-8")

    paths = uninstall.collect_output_cleanup_paths(tmp_path)

    names = {path.name for path in paths}
    assert "wallpaper_001.png" in names
    assert "origin_wallpaper_001.png" in names
    assert "note.txt" not in names


def test_cleanup_output_dir_removes_known_files_but_keeps_unknown_files(tmp_path: Path) -> None:
    known = tmp_path / "himawari.log"
    unknown = tmp_path / "note.txt"
    known.write_text("log", encoding="utf-8")
    unknown.write_text("keep", encoding="utf-8")

    removed = uninstall.cleanup_output_dir(tmp_path)

    removed_names = {path.name for path in removed}
    assert "himawari.log" in removed_names
    assert known.exists() is False
    assert unknown.exists() is True
    assert tmp_path.exists() is True


def test_cleanup_output_dir_removes_directory_when_empty(tmp_path: Path) -> None:
    known = tmp_path / "last_source_meta.json"
    known.write_text("{}", encoding="utf-8")

    removed = uninstall.cleanup_output_dir(tmp_path)

    assert known in removed
    assert tmp_path in removed
    assert tmp_path.exists() is False


def test_resolve_cleanup_output_dir_uses_config_file(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    config_path = tmp_path / "config.json"
    config_path.write_text('{"output_dir": "./runtime"}', encoding="utf-8")

    result = uninstall.resolve_cleanup_output_dir(None, config_path)

    assert result == (tmp_path / "runtime").resolve()


def test_build_conda_remove_command_uses_env_name() -> None:
    command = uninstall.build_conda_remove_command("conda", "himawari-wallpaper")

    assert command == ["conda", "env", "remove", "-n", "himawari-wallpaper", "-y"]


def test_cleanup_local_install_returns_summary(monkeypatch, tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    output_dir = tmp_path / "output"
    config_path.write_text("{}", encoding="utf-8")
    output_dir.mkdir()

    monkeypatch.setattr(uninstall, "remove_startup", lambda: True)
    monkeypatch.setattr(
        uninstall,
        "cleanup_output_dir",
        lambda path: [path / "wallpaper_001.png", path],
    )

    result = uninstall.cleanup_local_install(config_path=config_path, output_dir=output_dir)

    assert result.removed_startup is True
    assert len(result.removed_output_paths) == 2
    assert result.removed_config is True


def test_perform_cleanup_actions_honors_selected_flags(monkeypatch, tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    output_dir = tmp_path / "output"
    config_path.write_text("{}", encoding="utf-8")
    output_dir.mkdir()

    startup_calls: list[str] = []
    output_calls: list[Path] = []
    config_calls: list[Path | None] = []

    monkeypatch.setattr(
        uninstall,
        "remove_startup",
        lambda: startup_calls.append("startup") or True,
    )
    monkeypatch.setattr(
        uninstall,
        "cleanup_output_dir",
        lambda path: output_calls.append(path) or [path / "wallpaper_001.png"],
    )
    monkeypatch.setattr(
        uninstall,
        "remove_config_file",
        lambda path: config_calls.append(path) or True,
    )

    result = uninstall.perform_cleanup_actions(
        remove_startup_flag=False,
        remove_output_flag=True,
        remove_config_flag=False,
        config_path=config_path,
        output_dir=output_dir,
    )

    assert startup_calls == []
    assert output_calls == [output_dir]
    assert config_calls == []
    assert result.removed_startup is False
    assert len(result.removed_output_paths) == 1
    assert result.removed_config is False
