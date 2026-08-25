from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "kernel" / "templates" / "public-scripts" / "validate_public_product.py"


def _validator():
    spec = spec_from_file_location("public_product_validator_template", TEMPLATE)
    module = module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    "content",
    (
        "api_key: sk-abcdefghijklmnopqrstuv\n",
        "access_token=ghp_abcdefghijklmnopqrstuvwxyz\n",
        "-----BEGIN PRIVATE KEY-----\nsecret\n",
        "password: this-is-a-real-looking-secret\n",
    ),
)
def test_public_validator_rejects_credential_like_content(
    tmp_path: Path,
    content: str,
) -> None:
    validator = _validator()
    validator.ROOT = tmp_path
    (tmp_path / "leak.txt").write_text(content, encoding="utf-8")

    with pytest.raises(validator.ProductBoundaryError, match="forbidden public content"):
        validator.validate_content()


@pytest.mark.parametrize(
    "content",
    (
        "api_key: ${API_KEY}\n",
        "password: <placeholder>\n",
        "secret: your_example_secret\n",
    ),
)
def test_public_validator_allows_explicit_placeholders(tmp_path: Path, content: str) -> None:
    validator = _validator()
    validator.ROOT = tmp_path
    (tmp_path / "example.txt").write_text(content, encoding="utf-8")

    validator.validate_content()


def test_public_validator_scans_extensionless_and_dotfiles(tmp_path: Path) -> None:
    validator = _validator()
    validator.ROOT = tmp_path
    (tmp_path / ".gitignore").write_text("RoOt" + "-AzOtH\n", encoding="utf-8")

    with pytest.raises(validator.ProductBoundaryError, match="forbidden public content"):
        validator.validate_content()
