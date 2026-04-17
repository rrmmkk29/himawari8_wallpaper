import importlib.util
from pathlib import Path


def load_bootstrap_module():
    repo_root = Path(__file__).resolve().parents[1]
    module_path = repo_root / "scripts" / "bootstrap.py"
    spec = importlib.util.spec_from_file_location("bootstrap", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_build_conda_create_command_uses_env_name_and_python_version() -> None:
    module = load_bootstrap_module()

    command = module.build_conda_create_command("conda", "himawari-wallpaper", "3.11")

    assert command == [
        "conda",
        "create",
        "-y",
        "-n",
        "himawari-wallpaper",
        "python=3.11",
        "pip",
    ]


def test_build_conda_run_command_wraps_subcommand() -> None:
    module = load_bootstrap_module()

    command = module.build_conda_run_command(
        "conda",
        "himawari-wallpaper",
        ["python", "-m", "pip", "install", "-e", "."],
    )

    assert command == [
        "conda",
        "run",
        "--no-capture-output",
        "-n",
        "himawari-wallpaper",
        "python",
        "-m",
        "pip",
        "install",
        "-e",
        ".",
    ]


def test_parse_args_defaults_to_conda(monkeypatch) -> None:
    module = load_bootstrap_module()
    monkeypatch.setattr(module.sys, "argv", ["bootstrap.py"])

    args = module.parse_args()

    assert args.manager == "conda"
    assert args.conda_env_name == module.DEFAULT_CONDA_ENV


def test_environment_yml_declares_default_conda_env() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    text = (repo_root / "environment.yml").read_text(encoding="utf-8")

    assert "name: himawari-wallpaper" in text
    assert "- conda-forge" in text
