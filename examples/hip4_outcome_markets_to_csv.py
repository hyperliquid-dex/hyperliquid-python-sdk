import csv
from datetime import datetime, timezone, timedelta
from typing import Optional

from hyperliquid.info import Info
from hyperliquid.utils import constants


OUTPUT_CSV = "hip4_outcome_markets.csv"
INTERVAL = "1h"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def to_ms(dt: datetime) -> int:
    return int(dt.timestamp() * 1000)


def fmt_time(dt: datetime) -> str:
    return dt.replace(microsecond=0).strftime("%Y-%m-%d %H:%M:%S UTC")


def parse_description(description: str) -> dict:
    """
    Example:
    class:priceBinary|underlying:BTC|expiry:20260506-0600|targetPrice:80930|period:1d
    """
    parsed = {}

    for part in description.split("|"):
        if ":" in part:
            key, value = part.split(":", 1)
            parsed[key] = value

    return parsed


def parse_expiry(expiry: str) -> Optional[datetime]:
    """
    Example:
    20260506-0600 -> 2026-05-06 06:00 UTC
    """
    if not expiry:
        return None

    return datetime.strptime(expiry, "%Y%m%d-%H%M").replace(tzinfo=timezone.utc)


def parse_period(period: str) -> timedelta:
    """
    Handles simple periods such as:
    1d, 1h, 3m
    """
    if not period:
        return timedelta(days=1)

    amount = int(period[:-1])
    unit = period[-1].lower()

    if unit == "d":
        return timedelta(days=amount)
    if unit == "h":
        return timedelta(hours=amount)
    if unit == "m":
        return timedelta(minutes=amount)

    raise ValueError(f"Unsupported period: {period}")


def get_market_window(description: str, now: datetime) -> tuple[datetime, datetime]:
    """
    Uses the HIP-4 market description to estimate the relevant market window.

    Example:
    expiry: 20260506-0600
    period: 1d

    Window:
    2026-05-05 06:00 UTC -> 2026-05-06 06:00 UTC

    If the market has not expired yet, end the window at the current time.
    """
    parsed = parse_description(description)

    expiry = parse_expiry(parsed.get("expiry", ""))
    period = parse_period(parsed.get("period", "1d"))

    if expiry is None:
        return now - timedelta(days=1), now

    start = expiry - period
    end = min(expiry, now)

    return start, end


def fetch_candles(
    info: Info,
    coin: str,
    start_time: datetime,
    end_time: datetime,
    interval: str,
) -> list[dict]:
    return info.post(
        "/info",
        {
            "type": "candleSnapshot",
            "req": {
                "coin": coin,
                "interval": interval,
                "startTime": to_ms(start_time),
                "endTime": to_ms(end_time),
            },
        },
    )


def candle_volume(candles: list[dict]) -> float:
    return sum(float(candle.get("v", 0)) for candle in candles)


def candle_trade_count(candles: list[dict]) -> int:
    return sum(int(candle.get("n", 0)) for candle in candles)


def approx_notional(candles: list[dict]) -> float:
    """
    Approximate notional volume.

    This uses:
        candle close price * candle volume

    For exact notional, use trade-level data instead.
    """
    total = 0.0

    for candle in candles:
        close_price = float(candle.get("c", 0))
        volume = float(candle.get("v", 0))
        total += close_price * volume

    return total


def hip4_coin(outcome_id: int, side_index: int) -> str:
    """
    HIP-4 outcome asset encoding.

    Example:
    outcome_id = 3, side_index = 0 -> #30
    outcome_id = 3, side_index = 1 -> #31
    """
    return f"#{10 * outcome_id + side_index}"


def main() -> None:
    info = Info(constants.MAINNET_API_URL, skip_ws=True)
    now = utc_now()

    outcome_meta = info.post("/info", {"type": "outcomeMeta"})
    outcomes = outcome_meta.get("outcomes", [])

    rows = []

    print()
    print("HIP-4 Outcome Markets")
    print("=" * 100)
    print(f"Snapshot time: {fmt_time(now)}")
    print(f"Markets found: {len(outcomes)}")
    print()

    for market in outcomes:
        outcome_id = int(market["outcome"])
        market_name = market.get("name", "")
        description = market.get("description", "")
        side_specs = market.get("sideSpecs", [])

        parsed = parse_description(description)
        window_start, window_end = get_market_window(description, now)

        market_rows = []
        market_contract_volume = 0.0
        market_trade_count = 0
        market_approx_notional = 0.0

        print("-" * 100)
        print(f"Outcome ID:   {outcome_id}")
        print(f"Name:         {market_name}")
        print(f"Underlying:   {parsed.get('underlying', '')}")
        print(f"Expiry:       {parsed.get('expiry', '')}")
        print(f"Target price: {parsed.get('targetPrice', '')}")
        print(f"Period:       {parsed.get('period', '')}")
        print(f"Window:       {fmt_time(window_start)} -> {fmt_time(window_end)}")
        print()

        for side_index, side in enumerate(side_specs):
            side_name = side.get("name", f"Side {side_index}")
            coin = hip4_coin(outcome_id, side_index)

            candles = fetch_candles(
                info=info,
                coin=coin,
                start_time=window_start,
                end_time=window_end,
                interval=INTERVAL,
            )

            side_contract_volume = candle_volume(candles)
            side_trade_count = candle_trade_count(candles)
            side_approx_notional = approx_notional(candles)

            market_contract_volume += side_contract_volume
            market_trade_count += side_trade_count
            market_approx_notional += side_approx_notional

            market_rows.append(
                {
                    "snapshot_time_utc": fmt_time(now),
                    "window_start_utc": fmt_time(window_start),
                    "window_end_utc": fmt_time(window_end),
                    "outcome_id": outcome_id,
                    "market_name": market_name,
                    "market_class": parsed.get("class", ""),
                    "underlying": parsed.get("underlying", ""),
                    "expiry": parsed.get("expiry", ""),
                    "target_price": parsed.get("targetPrice", ""),
                    "period": parsed.get("period", ""),
                    "side_index": side_index,
                    "side_name": side_name,
                    "coin": coin,
                    "side_contract_volume": side_contract_volume,
                    "side_trade_count": side_trade_count,
                    "side_approx_notional": side_approx_notional,
                    "market_description": description,
                }
            )

            print(
                f"{side_name:<8} {coin:<8} "
                f"candles={len(candles):<4} "
                f"contracts={side_contract_volume:,.4f} "
                f"trades={side_trade_count:,} "
                f"approx_notional={side_approx_notional:,.4f}"
            )

        print()
        print(f"Market contract volume: {market_contract_volume:,.4f}")
        print(f"Market trades:          {market_trade_count:,}")
        print(f"Market approx notional: {market_approx_notional:,.4f}")
        print()

        for row in market_rows:
            row["market_contract_volume"] = market_contract_volume
            row["market_trade_count"] = market_trade_count
            row["market_approx_notional"] = market_approx_notional
            rows.append(row)

    rows.sort(
        key=lambda row: (
            float(row["market_contract_volume"]),
            float(row["side_contract_volume"]),
        ),
        reverse=True,
    )

    fieldnames = [
        "snapshot_time_utc",
        "window_start_utc",
        "window_end_utc",
        "outcome_id",
        "market_name",
        "market_class",
        "underlying",
        "expiry",
        "target_price",
        "period",
        "side_index",
        "side_name",
        "coin",
        "side_contract_volume",
        "side_trade_count",
        "side_approx_notional",
        "market_contract_volume",
        "market_trade_count",
        "market_approx_notional",
        "market_description",
    ]

    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    total_contract_volume = sum(float(row["side_contract_volume"]) for row in rows)
    total_trade_count = sum(int(row["side_trade_count"]) for row in rows)
    total_approx_notional = sum(float(row["side_approx_notional"]) for row in rows)

    print("=" * 100)
    print("Totals")
    print("=" * 100)
    print(f"Total contract volume: {total_contract_volume:,.4f}")
    print(f"Total trades:          {total_trade_count:,}")
    print(f"Total approx notional: {total_approx_notional:,.4f}")
    print()
    print(f"CSV written to: {OUTPUT_CSV}")
    print()


if __name__ == "__main__":
    main()