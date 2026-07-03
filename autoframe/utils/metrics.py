"""Metrics collection utilities."""

import time
from contextlib import contextmanager
from dataclasses import dataclass, field


@dataclass
class Timer:
    _start: float = 0
    _elapsed: float = 0

    def start(self):
        self._start = time.perf_counter()

    def stop(self) -> float:
        self._elapsed = time.perf_counter() - self._start
        return self._elapsed * 1000

    @property
    def elapsed_ms(self) -> float:
        return self._elapsed * 1000


@contextmanager
def timed():
    t = Timer()
    t.start()
    yield t
    t.stop()


@dataclass
class Counter:
    _value: int = 0

    def increment(self, n: int = 1):
        self._value += n

    @property
    def value(self) -> int:
        return self._value

    def reset(self):
        self._value = 0


@dataclass
class Stats:
    _values: list[float] = field(default_factory=list)

    def record(self, value: float):
        self._values.append(value)

    def clear(self):
        self._values.clear()

    @property
    def count(self) -> int:
        return len(self._values)

    @property
    def sum(self) -> float:
        return sum(self._values)

    @property
    def avg(self) -> float:
        if not self._values:
            return 0.0
        return self.sum / self.count

    @property
    def min(self) -> float:
        return min(self._values) if self._values else 0.0

    @property
    def max(self) -> float:
        return max(self._values) if self._values else 0.0

    @property
    def median(self) -> float:
        return self.percentile(50)

    def percentile(self, p: int) -> float:
        if not self._values:
            return 0.0
        sorted_vals = sorted(self._values)
        index = int(len(sorted_vals) * p / 100)
        index = min(index, len(sorted_vals) - 1)
        return sorted_vals[index]

    def as_dict(self) -> dict:
        return {
            "count": self.count, "avg": round(self.avg, 2),
            "min": round(self.min, 2), "max": round(self.max, 2),
            "p50": round(self.median, 2), "p90": round(self.percentile(90), 2),
            "p99": round(self.percentile(99), 2),
        }
