"""AICH experimental LONG observation scanner. Public data only; no orders."""
import argparse
import datetime as dt
import json
import math
import pathlib
import statistics
import time
import urllib.parse
import urllib.request

BASE = 'https://data-api.binance.vision'
STEP = 300_000
THRESHOLDS = dict(min_15m=0.006, min_acceleration=0.004,
                  min_volume_ratio=2.0, min_relative_15m=0.003,
                  max_1h=0.08, max_spread=0.003, min_daily_quote=5_000_000)


def get(endpoint, **params):
    url = BASE + '/api/v3/' + endpoint + '?' + urllib.parse.urlencode(params)
    request = urllib.request.Request(url, headers={'User-Agent': 'ProfitPilot/0.1'})
    # HTTP failures, including regional restrictions and rate limits, are surfaced.
    with urllib.request.urlopen(request, timeout=25) as response:
        return json.load(response)


def candles(raw, now):
    rows = []
    for r in raw:
        if int(r[6]) >= now:
            continue
        row = dict(t=int(r[0]), end=int(r[6]), high=float(r[2]),
                   low=float(r[3]), close=float(r[4]), quote=float(r[7]))
        if not all(math.isfinite(row[k]) for k in ('high', 'low', 'close', 'quote')):
            raise ValueError('Non-finite candle')
        if not 0 < row['low'] <= row['close'] <= row['high'] or row['quote'] < 0:
            raise ValueError('Invalid candle prices or volume')
        rows.append(row)
    rows = rows[-61:]
    if len(rows) < 61:
        raise ValueError('Need 61 closed five-minute candles')
    if any(b['t'] - a['t'] != STEP for a, b in zip(rows, rows[1:])):
        raise ValueError('Missing or duplicate candles')
    if any(r['end'] != r['t'] + STEP - 1 for r in rows):
        raise ValueError('Invalid candle interval')
    if not 0 < now - rows[-1]['end'] <= STEP + 60_000:
        raise ValueError('Stale or future data')
    return rows


def evaluate(rows, btc, spread, daily_quote):
    if rows[-1]['t'] != btc[-1]['t']:
        raise ValueError('BTC benchmark candle not aligned')
    if not all(math.isfinite(v) and v >= 0 for v in (spread, daily_quote)):
        raise ValueError('Invalid liquidity data')
    p = [r['close'] for r in rows]
    r15 = p[-1] / p[-4] - 1
    previous = p[-4] / p[-7] - 1
    r60 = p[-1] / p[-13] - 1
    base_vol = statistics.median(sum(r['quote'] for r in rows[i:i+3])
                                 for i in range(0, 57, 3))
    if base_vol <= 0:
        raise ValueError('Empty volume baseline')
    ratio = sum(r['quote'] for r in rows[-3:]) / base_vol
    relative = r15 - (btc[-1]['close'] / btc[-4]['close'] - 1)
    checks = dict(momentum=r15 >= THRESHOLDS['min_15m'],
                  acceleration=r15-previous >= THRESHOLDS['min_acceleration'],
                  volume=ratio >= THRESHOLDS['min_volume_ratio'],
                  breakout=p[-1] > max(r['high'] for r in rows[-25:-1]),
                  relative_strength=relative >= THRESHOLDS['min_relative_15m'],
                  not_overextended=0 < r60 <= THRESHOLDS['max_1h'],
                  spread=spread <= THRESHOLDS['max_spread'],
                  liquidity=daily_quote >= THRESHOLDS['min_daily_quote'])
    return dict(status='LONG_WATCH' if all(checks.values()) else 'NO_SIGNAL',
                checks=checks, close=p[-1], return_15m=r15, return_1h=r60,
                acceleration=r15-previous, volume_ratio=ratio,
                relative_15m=relative, spread=spread, candle_open_ms=rows[-1]['t'])


def run(limit, output):
    now = int(get('time')['serverTime'])
    info = get('exchangeInfo')
    eligible = {r['symbol'] for r in info['symbols']
                if r['status'] == 'TRADING' and r['quoteAsset'] == 'USDT'
                and r.get('isSpotTradingAllowed', False)
                and r['baseAsset'] not in {'USDC', 'DAI', 'TUSD', 'FDUSD', 'USDP', 'USDE', 'USD1'}}
    tickers = [r for r in get('ticker/24hr') if r['symbol'] in eligible
               and float(r['quoteVolume']) >= THRESHOLDS['min_daily_quote']]
    tickers.sort(key=lambda r: float(r['quoteVolume']), reverse=True)
    selected = tickers[:limit]
    books = {r['symbol']: r for r in get('ticker/bookTicker')}
    btc = candles(get('klines', symbol='BTCUSDT', interval='5m', limit=65), now)
    result = dict(version='0.1-experimental', mode='OBSERVATION', orders_enabled=False,
                  generated_at_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
                  thresholds=THRESHOLDS, universe_count=len(eligible),
                  selected_count=len(selected), rows=[], errors=[])
    for ticker in selected:
        symbol = ticker['symbol']
        try:
            # Use one server-time cutoff for the entire scan.
            rows = candles(get('klines', symbol=symbol, interval='5m', limit=65), now)
            book = books[symbol]
            bid, ask = float(book['bidPrice']), float(book['askPrice'])
            if not 0 < bid <= ask:
                raise ValueError('Invalid bid/ask')
            report = evaluate(rows, btc, (ask-bid)/((ask+bid)/2), float(ticker['quoteVolume']))
            result['rows'].append(dict(symbol=symbol, **report))
        except Exception as error:
            result['errors'].append(dict(symbol=symbol, error=str(error)))
        time.sleep(0.15)
    if not result['rows']:
        raise RuntimeError('No markets evaluated successfully')
    result['health'] = 'DEGRADED' if result['errors'] else 'OK'
    output.mkdir(parents=True, exist_ok=True)
    (output / 'latest.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    signals = [r for r in result['rows'] if r['status'] == 'LONG_WATCH']
    print(json.dumps(dict(health=result['health'], evaluated=len(result['rows']),
                         signals=signals, errors=result['errors']), indent=2))
    return 2 if result['errors'] else 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--limit', type=int, default=50)
    parser.add_argument('--output', type=pathlib.Path, default=pathlib.Path('reports'))
    args = parser.parse_args()
    if not 1 <= args.limit <= 200:
        parser.error('--limit must be 1..200')
    raise SystemExit(run(args.limit, args.output))
