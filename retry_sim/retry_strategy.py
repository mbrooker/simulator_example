from os import O_NONBLOCK


class NRetriesStrategy:
    def __init__(self, N):
        self.N = N
        self.n_tries = 0

    def new_call(self):
        return NRetriesStrategy(self.N)

    def start(self):
        pass

    def should_retry(self):
        self.n_tries += 1
        return self.n_tries <= self.N

class NRetriesFactory(object):
    def __init__(self, N):
        self.N = N

    def make(self):
        return NRetriesStrategy(self.N)

class AdaptiveRetryStrategy(object):
    def __init__(self, bucket_fill_rate, bucket_size):
        self.bucket_size = bucket_size
        self.bucket_fill_rate = bucket_fill_rate
        self.bucket = bucket_size

    def new_call(self):
        return self

    def start(self):
        self.bucket = min(self.bucket + self.bucket_fill_rate, self.bucket_size)

    def should_retry(self):
        if self.bucket > 1.0:
            self.bucket -= 1.0
            return True
        else:
            return False

class AdaptiveRetryFactory(object):
    def __init__(self, bucket_fill_rate, bucket_size):
        self.bucket_size = bucket_size
        self.bucket_fill_rate = bucket_fill_rate

    def make(self):
        return AdaptiveRetryStrategy(self.bucket_fill_rate, self.bucket_size)

class CircuitBreakerRetryCall(object):
    def __init__(self, cbrs, nrs):
        self.cbrs = cbrs
        self.nrs = nrs

    def start(self):
        self.cbrs.calls += 1.0

    def should_retry(self):
        self.cbrs.failures += 1.0
        if (self.cbrs.failures / self.cbrs.calls) > self.cbrs.max_rate:
            return False
        else:
            return self.nrs.should_retry()

class CircuitBreakerRetryStrategy(object):
    def __init__(self, n_retries_strategy, max_rate):
        self.n_retries_strategy = n_retries_strategy
        self.max_rate = max_rate
        self.calls = 0.0
        self.failures = 0.0

    def new_call(self):
        return CircuitBreakerRetryCall(self, self.n_retries_strategy.new_call())

class CircuitBreakerRetryFactory(object):
    def __init__(self, n_retries_factory, max_rate):
        self.n_retries_factory = n_retries_factory
        self.max_rate = max_rate

    def make(self):
        return CircuitBreakerRetryStrategy(self.n_retries_factory.make(), self.max_rate)