# {{PRODUCT_NAME}}

{{DESCRIPTION}}

## Install (consumer project)

From a clone of this repository:

```bash
pip install -r requirements-dev.txt   # or your venv equivalent
bash install.sh                         # or install.ps1 on Windows — project mode
```

Then open **`CLAUDE.md`** in your AI tool and follow the bootloader (**ACTIVATE → SURVEY → OPERATE → HARDEN**).

## What this repo is

**{{PRODUCT_NAME}}** is the public, installable Azoth toolkit (see architecture docs in `docs/`). It is extracted from the private **root-azoth** workshop using `scripts/azoth_extract_product.py` and `sync-config.yaml` (`product_extraction`).

## License

Licensed under the [PolyForm Noncommercial License 1.0.0](https://polyformproject.org/licenses/noncommercial/1.0.0/). The copyright holder retains all rights not expressly granted. **Commercial use** (outside the license’s permitted noncommercial purposes) requires a **separate written agreement** — contact via [github.com/yiwei79](https://github.com/yiwei79).

## Contributing / upstream

Development happens in the **root-azoth** scaffold; changes here flow from mechanical extraction — do not treat this tree as the authoritative workshop copy.
