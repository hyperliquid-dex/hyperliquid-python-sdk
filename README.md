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

## Quick Start

```python
from hyperliquid.info import Info
from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants
import eth_account

# Create wallet from private key
wallet = eth_account.Account.from_key("your_private_key")

# Initialize Info and Exchange instances
info = Info(constants.TESTNET_API_URL)  # Use MAINNET_API_URL for mainnet
exchange = Exchange(wallet, constants.TESTNET_API_URL)

# Get user state
user_state = info.user_state(wallet.address)
print(user_state)

# Place a limit order
order_result = exchange.order(
    name="ETH",        # Asset name
    is_buy=True,       # True for buy, False for sell
    sz=0.1,            # Order size
    limit_px=1800,     # Limit price
    order_type={"limit": {"tif": "Gtc"}}  # Good-till-cancel order
)
```

## Core Concepts

### Info Class

The `Info` class provides methods to query market data and user information. The full [API specs](https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/info-endpoint) are available in the documentation.

```python
from hyperliquid.info import Info

info = Info(constants.TESTNET_API_URL)

# Get order book
l2_book = info.l2_book("ETH")

# Get user's open orders
open_orders = info.open_orders(wallet.address)

# Get all asset mid prices
mid_prices = info.all_mids()
```

### Exchange Class

The `Exchange` class handles all trading operations.  The full [API specs](https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/exchange-endpoint) are available in the documentation.

```python
from hyperliquid.exchange import Exchange

exchange = Exchange(wallet, constants.TESTNET_API_URL)

# Market order
exchange.market_open(
    name="BTC",
    is_buy=True,
    sz=0.01,
    slippage=0.001  # 0.1% slippage tolerance
)

# Close position
exchange.market_close("BTC")

# Cancel order
exchange.cancel("ETH", order_id)
```

### Websockets
The SDK provides real-time market data and user events through WebSocket connections. The WebSocket manager automatically handles connection maintenance and reconnection.  The full specs are available on the [documentation](https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/websocket/subscriptions).

#### Basic Websockets Connection
```python
from hyperliquid.info import Info
from hyperliquid.utils import constants

def handle_orderbook(message):
    bids, asks = message["data"]
    print(f"Top bid: {bids[0]['px']} | Top ask: {asks[0]['px']}")

def handle_trades(message):
    for trade in message["data"]:
        print(f"Trade: {trade['sz']} @ {trade['px']}")

def handle_user_events(message):
    print(f"User event: {message}")

# Initialize Info instance with WebSocket support
info = Info(constants.TESTNET_API_URL)

# Subscribe to different data streams
info.subscribe(
    {"type": "l2Book", "coin": "ETH"}, 
    handle_orderbook
)

info.subscribe(
    {"type": "trades", "coin": "BTC"}, 
    handle_trades
)

info.subscribe(
    {"type": "userEvents", "user": wallet.address}, 
    handle_user_events
)

# The WebSocket connection will remain active and process messages
# until the program exits or the connection is explicitly closed
```

#### Available Subscription Types
1. Market Data

```python
# All mid prices
info.subscribe({"type": "allMids"}, callback)

# L2 Order Book for specific asset
info.subscribe({"type": "l2Book", "coin": "ETH"}, callback)

# Recent trades for specific asset
info.subscribe({"type": "trades", "coin": "BTC"}, callback)

# Candlestick data
info.subscribe({
    "type": "candle", 
    "coin": "ETH", 
    "interval": "1m"  # Available intervals: 1m, 5m, 15m, 1h, 4h, 1d
}, callback)
```

2. User
```python
# All user events (orders, fills, etc.)
info.subscribe({"type": "userEvents", "user": wallet.address}, callback)

# User trade fills
info.subscribe({"type": "userFills", "user": wallet.address}, callback)

# Order status updates
info.subscribe({"type": "orderUpdates", "user": wallet.address}, callback)

# Funding payments
info.subscribe({"type": "userFundings", "user": wallet.address}, callback)

# Non-funding ledger updates
info.subscribe({"type": "userNonFundingLedgerUpdates", "user": wallet.address}, callback)

# Web data updates
info.subscribe({"type": "webData2", "user": wallet.address}, callback)
```

#### Message Formats
1. L2 Book

```python
{
    "channel": "l2Book",
    "data": [
        # Bids array
        [
            {"px": "1900.5", "sz": "1.5", "n": 3},  # price, size, number of orders
            # ... more bid levels
        ],
        # Asks array
        [
            {"px": "1901.0", "sz": "2.1", "n": 2},
            # ... more ask levels
        ]
    ]
}
```

2. Trades
```python
{
    "channel": "trades",
    "data": [
        {
            "coin": "ETH",
            "side": "A",  # "A" for ask (sell), "B" for bid (buy)
            "px": "1900.5",
            "sz": "1.5",
            "hash": "0x...",
            "timestamp": 1234567890
        }
        # ... more trades
    ]
}
```

3. User
```python
{
    "channel": "userEvents",
    "data": {
        "type": "fill",  # or "order", "cancel", etc.
        "data": {
            # Event specific data
            "oid": 123,
            "px": "1900.5",
            "sz": "1.5",
            # ... other fields
        }
    }
}
```

#### Websocket Management
The WebSocket connection is automatically managed by the SDK, but you can control it if needed:

```python
# Initialize Info with WebSocket support
info = Info(constants.TESTNET_API_URL)

# Access the WebSocket manager
ws_manager = info.ws_manager

# Check connection status
is_connected = ws_manager.is_connected()

# Manually reconnect if needed
ws_manager.reconnect()

# Close WebSocket connection
ws_manager.close()
```

#### Error Handling in WebSocket Callbacks
```python
def safe_callback(message):
    try:
        # Process the message
        print(f"Received: {message}")
        
        # Add your processing logic here
        if message["channel"] == "l2Book":
            bids, asks = message["data"]
            # Process order book data
        elif message["channel"] == "trades":
            # Process trades data
            pass
            
    except Exception as e:
        print(f"Error processing message: {e}")
        # Handle the error appropriately
        
# Subscribe with error-handled callback
info.subscribe({"type": "l2Book", "coin": "ETH"}, safe_callback)
```

## Advanced Features

### Vault/SubAccount Trading
```python
# Create Exchange instance with vault address
vault_exchange = Exchange(wallet, base_url, vault_address="vault_address")

# Place order through vault
vault_exchange.order("ETH", True, 0.1, 1800, {"limit": {"tif": "Gtc"}})
```

### Client Order ID (cloid)

```python
from hyperliquid.utils.types import Cloid

# Create CLOID
cloid = Cloid.from_str("0x00000000000000000000000000000001")

# Place order with CLOID
exchange.order(
    "ETH", 
    True, 
    0.1, 
    1800, 
    {"limit": {"tif": "Gtc"}}, 
    cloid=cloid
)

# Query order by CLOID
order_status = info.query_order_by_cloid(wallet.address, cloid)
```

## Error Handling
The SDK uses custom error classes for better error handling:

```python
from hyperliquid.utils.error import ClientError, ServerError

try:
    result = exchange.order(...)
except ClientError as e:
    print(f"Client error: {e.error_message}")
except ServerError as e:
    print(f"Server error: {e.message}")
```


## Usage Examples

Check out the [examples](examples) directory for more complete examples:
- Basic order placement and management
- Market making strategies
- WebSocket usage
- Vault trading
- Leverage adjustment
- Asset transfers

```python
from hyperliquid.info import Info
from hyperliquid.utils import constants

info = Info(constants.TESTNET_API_URL, skip_ws=True)
user_state = info.user_state("0xcd5051944f780a621ee62e39e493c489668acf4d")
print(user_state)
```

You can also checkout the repo and run any of the examples after configuring your private key e.g. 
```bash
# Create a copy of the config template
cp examples/config.json.example examples/config.json

# Update the config with your key
vim examples/config.json

# Run a basic order
python examples/basic_order.py
```

## Getting started with contributing to this repo

1. Download `Poetry`: https://python-poetry.org/. 
   - Note that in the install script you might have to set `symlinks=True` in `venv.EnvBuilder`.
   - Note that Poetry v2 is not supported, so you'll need to specify a specific version e.g. curl -sSL https://install.python-poetry.org | POETRY_VERSION=1.4.1 python3 - 

2. Point poetry to correct version of python. For development we require python 3.10 exactly. Some dependencies have issues on 3.11, while older versions don't have correct typing support.
`brew install python@3.10 && poetry env use /opt/homebrew/Cellar/python@3.10/3.10.16/bin/python3.10`

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
  year = {2024},
  publisher = {GitHub},
  journal = {GitHub repository},
  howpublished = {\url{https://github.com/hyperliquid-dex/hyperliquid-python-sdk}}
}
```

## Credits

This project was generated with [`python-package-template`](https://github.com/TezRomacH/python-package-template).
