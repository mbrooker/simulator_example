import random
import math

def net_rtt():
    return random.expovariate(1 / 0.01)

# Client that starts calls at `rate_rps` (with exponentially distributed per-call gaps).
#  No concurrency limit, no backoff.
class Client(object):
    def __init__(self, retry_strategy, rate_rps, server, stats, retry_backoff):
        self.retry_strategy = retry_strategy
        self.rate = rate_rps
        self.server = server
        self.stats = stats
        self.retry_backoff = retry_backoff
        self.drain = False

    def gen_load(self, _payload, t):
        call = Call(self.retry_strategy, self.server, self.stats, self, self.retry_backoff)
        if self.drain:
            return [] 
        else: 
            return [(t + random.expovariate(self.rate), self.gen_load, None),
                    (t, call.start, None)]

    def done_success(self, t):
        return []

    def done_failure(self, t):
        return []


# Serial client that starts a call (approximately at `rate_rps`), but only keeps one call in flight at
#  a time.
class SerialClient(object):
    def __init__(self, retry_strategy, rate_rps, server, stats, retry_backoff):
        self.retry_strategy = retry_strategy
        self.rate = rate_rps
        self.server = server
        self.stats = stats
        self.retry_backoff = retry_backoff
        self.drain = False
        self.last_call_start = 0

    def gen_load(self, _payload, t):
        call = Call(self.retry_strategy, self.server, self.stats, self, self.retry_backoff)
        if self.drain:
            return [] 
        else:
            # Start the next call immediately if we've waited too long, or after the right delay to get the right
            #  overall rate if we haven't waited too long.
            next_t_delay = max(0.0, random.expovariate(self.rate) - t + self.last_call_start)
            next_t = t + next_t_delay
            self.last_call_start = next_t
            return [(next_t, call.start, None)]

    def done_success(self, t):
        return self.gen_load(None, t)

    def done_failure(self, t):
        return self.gen_load(None, t)

# Serial client that starts a call (approximately at `rate_rps`), but only keeps one call in flight at
#  a time. Additionally, when it sees failures, it performs uncapped exponential backoff.
# (Real clients will jitter their backoff. We don't do that here because our server is insensitive to load, 
#  a somewhat unrealistic simplification in the simulation)
class SerialClientWithBackoff(object):
    def __init__(self, retry_strategy, rate_rps, server, stats, retry_backoff):
        self.retry_strategy = retry_strategy
        self.rate = rate_rps
        self.server = server
        self.stats = stats
        self.base_backoff = 1.0 / rate_rps
        self.current_backoff = self.base_backoff
        self.retry_backoff = retry_backoff
        self.drain = False

    def gen_load(self, _payload, t):
        call = Call(self.retry_strategy, self.server, self.stats, self, self.retry_backoff)
        if self.drain:
            return [] 
        else: 
            return [(t + random.expovariate(self.rate), call.start, None)]

    def done_success(self, t):
        # We've seen a success. Reset the backoff to the base, and send the next call immediately
        self.current_backoff = self.base_backoff
        return self.gen_load(None, t)

    def done_failure(self, t):
        # We've seen a failure. Send the next call only after the backoff period, and increase the backoff
        event = [(t + self.current_backoff, self.gen_load, None)]
        self.current_backoff *= 2
        #print("backoff is", self.current_backoff)
        return event


class Call(object):
    def __init__(self, retry_strategy, server, stats, client, base_backoff):
        self.retry_strategy = retry_strategy.new_call()
        self.server = server
        self.stats = stats
        self.client = client
        self.base_backoff = base_backoff

    def start(self, _payload, t):
        self.retry_strategy.start()
        self.stats.first_try()
        return [(t + net_rtt(), self.server.handle, self)]
        

    def done_success(self, _payload, t):
        self.stats.success()
        # This call was successful, inform the client
        return self.client.done_success(t)

    def done_failure(self, _payload, t):
        if self.retry_strategy.should_retry():
            self.stats.retry()
            # The call failed, but we decided to retry, so queue up another attempt with the server, and exponentially increase our backoff
            work = [(t + net_rtt() + self.base_backoff, self.server.handle, self)]
            self.base_backoff *= 2
            return work
        else:
            # The call failed, we're not retrying, so just go back to the client and tell them the bad news
            return self.client.done_failure(t)

