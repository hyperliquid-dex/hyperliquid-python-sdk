# hyperliquid-python-sdk

<div align="center">

[![Dependencies Status](https://img.shields.io/badge/dependencies-up%20to%20date-brightgreen.svg)](https://github.com/hyperliquid-dex/hyperliquid-python-sdk/pulls?utf8=%E2%9C%93&q=is%3Apr%20author%3Aapp%2Fdependabot)

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Security: bandit](https://img.shields.io/badge/security-bandit-green.svg)](https://github.com/PyCQA/bandit)
[![Pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/hyperliquid-dex/hyperliquid-python-sdk/blob/master/.pre-commit-config.yaml)
[![Semantic Versions](https://img.shields.io/badge/%20%20%F0%9F%93%A6%F0%9F%9A%80-semantic--versions-e10079.svg)](https://github.com/hyperliquid-dex/hyperliquid-python-sdk/releases)
[![License](https://img.shields.io/pypi/l/hyperliquid-python-sdk)](https://github.com/hyperliquid-dex/hyperliquid-python-sdk/blob/master/LICENSE.md)
![Coverage Report](https://github.com/hyperliquid-dex/hyperliquid-python-sdk/blob/master/assets/images/coverage.svg)

SDK for Hyperliquid API trading with Python.

</div>

## Installation
```bash
pip install hyperliquid-python-sdk
```
## Configuration 

- Set the public key as the `account_address` in examples/config.json.
- Set your private key as the `secret_key` in examples/config.json.
- See the example of loading the config in examples/example_utils.py

### [Optional] Generate a new API key for an API Wallet
Generate and authorize a new API private key on https://app.hyperliquid.xyz/API, and set the API wallet's private key as the `secret_key` in examples/config.json. Note that you must still set the public key of the main wallet *not* the API wallet as the `account_address` in examples/config.json

## Usage Examples
```python
from hyperliquid.info import Info
from hyperliquid.utils import constants

info = Info(constants.TESTNET_API_URL, skip_ws=True)
user_state = info.user_state("0xcd5051944f780a621ee62e39e493c489668acf4d")
print(user_state)
```
See [examples](examples) for more complete examples. You can also checkout the repo and run any of the examples after configuring your private key e.g. 
```bash
cp examples/config.json.example examples/config.json
vim examples/config.json
python examples/basic_order.py
```

## Getting started with contributing to this repo

1. Download `Poetry`: https://python-poetry.org/. Note that in the install script you might have to set `symlinks=True` in `venv.EnvBuilder`.

2. Point poetry to correct version of python. For development we require python 3.10 exactly. Some dependencies have issues on 3.11, while older versions don't have correct typing support.
`brew install python@3.10 && poetry env use /opt/homebrew/Cellar/python@3.10/3.10.10_1/bin/python3.10`

3. Install dependencies:

```bash
make install
```

### Makefile usage

CLI commands for faster development.

<details>
<summary>Install all dependencies</summary>
<p>

Install requirements:

```bash
make install
```

</p>
</details>

<details>
<summary>Codestyle</summary>
<p>

Install pre-commit hooks which will run isort, black and codestyle on your code:

```bash
make pre-commit-install
```

Automatic formatting uses `pyupgrade`, `isort` and `black`.

```bash
make codestyle

# or use synonym
make formatting
```

Codestyle checks only, without rewriting files:

```bash
make check-codestyle
```

> Note: `check-codestyle` uses `isort`, `black` and `darglint` library

Update all dev libraries to the latest version using one command

```bash
make update-dev-deps
```

</p>
</details>

<details>
<summary>Tests with coverage badges</summary>
<p>

Run `pytest`

```bash
make test
```

</p>
</details>

<details>
<summary>All linters</summary>
<p>

```bash
make lint
```

the same as:

```bash
make test && make check-codestyle && make mypy && make check-safety
```

</p>
</details>

<details>
<summary>Cleanup</summary>
<p>
Delete pycache files

```bash
make pycache-remove
```

Remove package build

```bash
make build-remove
```

Delete .DS_STORE files

```bash
make dsstore-remove
```

Remove .mypycache

```bash
make mypycache-remove
```

Or to remove all above run:

```bash
make cleanup
```

</p>
</details>

## Releases

You can see the list of available releases on the [GitHub Releases](https://github.com/hyperliquid-dex/hyperliquid-python-sdk/releases) page.

We follow the [Semantic Versions](https://semver.org/) specification and use [`Release Drafter`](https://github.com/marketplace/actions/release-drafter). As pull requests are merged, a draft release is kept up-to-date listing the changes, ready to publish when you’re ready. With the categories option, you can categorize pull requests in release notes using labels.

### List of labels and corresponding titles

|               **Label**               |  **Title in Releases**  |
| :-----------------------------------: | :---------------------: |
|       `enhancement`, `feature`        |        Features         |
| `bug`, `refactoring`, `bugfix`, `fix` |  Fixes & Refactoring    |
|       `build`, `ci`, `testing`        |  Build System & CI/CD   |
|              `breaking`               |    Breaking Changes     |
|            `documentation`            |     Documentation       |
|            `dependencies`             |  Dependencies updates   |

### Building and releasing

Building a new version of the application contains steps:

- Bump the version of your package with `poetry version <version>`. You can pass the new version explicitly, or a rule such as `major`, `minor`, or `patch`. For more details, refer to the [Semantic Versions](https://semver.org/) standard.
- Make a commit to `GitHub`
- Create a `GitHub release`
- `poetry publish --build`

## License

This project is licensed under the terms of the `MIT` license. See [LICENSE](LICENSE.md) for more details.

```bibtex
@misc{hyperliquid-python-sdk,
  author = {Hyperliquid},
  title = {SDK for Hyperliquid API trading with Python.},
  year = {2023},
  publisher = {GitHub},
  journal = {GitHub repository},
  howpublished = {\url{https://github.com/hyperliquid-dex/hyperliquid-python-sdk}}
}
```

## Terms

By using this package you agree to the Terms of Use. See [TERMS](TERMS.md) for more details.
## Credits

This project was generated with [`python-package-template`](https://github.com/TezRomacH/python-package-template).
