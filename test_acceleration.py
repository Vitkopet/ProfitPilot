import unittest
from acceleration import candles, evaluate, STEP


def series():
    return [dict(t=i*STEP, end=(i+1)*STEP-1, low=99., high=100.1,
                 close=100., quote=100.) for i in range(61)]


class DetectorTests(unittest.TestCase):
    def test_positive_and_flat_benchmark(self):
        rows = series()
        rows[-1].update(close=101., high=101.1, quote=1000.)
        self.assertEqual(evaluate(rows, series(), .001, 10_000_000)['status'], 'LONG_WATCH')

    def test_flat_market_rejected(self):
        self.assertEqual(evaluate(series(), series(), .001, 10_000_000)['status'], 'NO_SIGNAL')

    def test_spread_blocks_signal(self):
        rows = series()
        rows[-1].update(close=101., high=101.1, quote=1000.)
        self.assertEqual(evaluate(rows, series(), .01, 10_000_000)['status'], 'NO_SIGNAL')

    def test_missing_candle_rejected(self):
        raw = [[i*STEP, 100, 101, 99, 100, 1, (i+1)*STEP-1, 100] for i in range(63)]
        del raw[40]
        with self.assertRaises(ValueError):
            candles(raw, 63*STEP)

    def test_open_candle_excluded(self):
        raw = [[i*STEP, 100, 101, 99, 100, 1, (i+1)*STEP-1, 100] for i in range(62)]
        rows = candles(raw, 61*STEP)
        self.assertEqual(rows[-1]['t'], 60*STEP)

    def test_stale_data_rejected(self):
        raw = [[i*STEP, 100, 101, 99, 100, 1, (i+1)*STEP-1, 100] for i in range(61)]
        with self.assertRaises(ValueError):
            candles(raw, 65*STEP)

    def test_misaligned_benchmark_rejected(self):
        btc = series()
        btc[-1]['t'] += STEP
        with self.assertRaises(ValueError):
            evaluate(series(), btc, .001, 10_000_000)


if __name__ == '__main__':
    unittest.main()
