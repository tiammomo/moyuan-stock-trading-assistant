from __future__ import annotations

from typing import List, Optional

from app.schemas import ChartConfig, ChartDataPoint
from .local_market_skill_client import LocalKlineBar


def build_chart_config(
    *,
    subject: Optional[str],
    bars: List[LocalKlineBar],
    chart_types: List[str],
) -> Optional[ChartConfig]:
    if not bars:
        return None

    closes = [bar.close_price for bar in bars]
    ma5 = _moving_average(closes, 5)
    ma10 = _moving_average(closes, 10)
    ma20 = _moving_average(closes, 20)
    dif, dea, macd = _macd(closes)
    rsi = _rsi(closes, 14)
    k_values, d_values, j_values = _kdj(bars, 9)

    items: List[ChartDataPoint] = []
    for index, bar in enumerate(bars):
        items.append(
            ChartDataPoint(
                time=bar.time,
                open=bar.open_price,
                high=bar.high_price,
                low=bar.low_price,
                close=bar.close_price,
                volume=bar.volume,
                ma5=ma5[index],
                ma10=ma10[index],
                ma20=ma20[index],
                dif=dif[index],
                dea=dea[index],
                macd=macd[index],
                rsi=rsi[index],
                k=k_values[index],
                d=d_values[index],
                j=j_values[index],
            )
        )

    return ChartConfig(
        subject=subject,
        chart_types=chart_types,
        items=items,
    )


def _moving_average(values: List[Optional[float]], window: int) -> List[Optional[float]]:
    result: List[Optional[float]] = []
    for index in range(len(values)):
        segment = [value for value in values[max(0, index - window + 1) : index + 1] if value is not None]
        result.append(sum(segment) / window if len(segment) == window else None)
    return result


def _ema(values: List[Optional[float]], window: int) -> List[Optional[float]]:
    result: List[Optional[float]] = []
    multiplier = 2 / (window + 1)
    previous: Optional[float] = None
    for value in values:
        if value is None:
            result.append(previous)
            continue
        if previous is None:
            previous = value
        else:
            previous = (value - previous) * multiplier + previous
        result.append(previous)
    return result


def _macd(values: List[Optional[float]]) -> tuple[List[Optional[float]], List[Optional[float]], List[Optional[float]]]:
    ema12 = _ema(values, 12)
    ema26 = _ema(values, 26)
    dif: List[Optional[float]] = []
    for fast, slow in zip(ema12, ema26):
        dif.append((fast - slow) if fast is not None and slow is not None else None)
    dea = _ema(dif, 9)
    macd = [(fast - slow) * 2 if fast is not None and slow is not None else None for fast, slow in zip(dif, dea)]
    return dif, dea, macd


def _rsi(values: List[Optional[float]], window: int) -> List[Optional[float]]:
    result: List[Optional[float]] = [None] * len(values)
    gains: List[float] = []
    losses: List[float] = []
    for index in range(1, len(values)):
        current = values[index]
        previous = values[index - 1]
        if current is None or previous is None:
            continue
        change = current - previous
        gains.append(max(change, 0))
        losses.append(abs(min(change, 0)))
        if len(gains) > window:
            gains.pop(0)
            losses.pop(0)
        if len(gains) < window:
            continue
        average_gain = sum(gains) / window
        average_loss = sum(losses) / window
        if average_loss == 0:
            result[index] = 100.0
            continue
        rs = average_gain / average_loss
        result[index] = 100 - (100 / (1 + rs))
    return result


def _kdj(
    bars: List[LocalKlineBar],
    window: int,
) -> tuple[List[Optional[float]], List[Optional[float]], List[Optional[float]]]:
    k_values: List[Optional[float]] = []
    d_values: List[Optional[float]] = []
    j_values: List[Optional[float]] = []
    prev_k = 50.0
    prev_d = 50.0

    for index, bar in enumerate(bars):
        segment = bars[max(0, index - window + 1) : index + 1]
        highs = [item.high_price for item in segment if item.high_price is not None]
        lows = [item.low_price for item in segment if item.low_price is not None]
        close = bar.close_price
        if not highs or not lows or close is None:
            k_values.append(None)
            d_values.append(None)
            j_values.append(None)
            continue
        highest = max(highs)
        lowest = min(lows)
        if highest == lowest:
            rsv = 50.0
        else:
            rsv = ((close - lowest) / (highest - lowest)) * 100
        current_k = (2 * prev_k + rsv) / 3
        current_d = (2 * prev_d + current_k) / 3
        current_j = 3 * current_k - 2 * current_d
        prev_k = current_k
        prev_d = current_d
        k_values.append(current_k)
        d_values.append(current_d)
        j_values.append(current_j)

    return k_values, d_values, j_values
