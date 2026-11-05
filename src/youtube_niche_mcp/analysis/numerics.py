"""Unrounded Decimal equations; type-7 quantiles and log robust baselines."""

from decimal import Decimal, localcontext


def ratio(n, d):
    if not d:
        return None
    with localcontext() as ctx:
        ctx.prec = 28
        return Decimal(n) / Decimal(d)


def quantile(values, q=Decimal("0.5")):
    items = sorted(Decimal(v) for v in values)
    if not items:
        return None
    with localcontext() as ctx:
        ctx.prec = 28
        index = (len(items) - 1) * q
        lo = int(index)
        hi = min(lo + 1, len(items) - 1)
        return items[lo] + (items[hi] - items[lo]) * (index - lo)


def log_baseline(values):
    with localcontext() as ctx:
        ctx.prec = 28
        return quantile([(Decimal(v) + 1).ln() for v in values])


def blend(channel_log, peer_log, n, k):
    weight = ratio(n, n + k)
    with localcontext() as ctx:
        ctx.prec = 28
        b = (weight * channel_log if n else Decimal(0)) + (1 - weight) * peer_log
        return b, b.exp() - 1, weight


def json_numbers(value):
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {k: json_numbers(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [json_numbers(v) for v in value]
    return value
