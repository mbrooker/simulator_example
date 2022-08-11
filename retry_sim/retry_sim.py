import random
import heapq

from retry_strategy import AdaptiveRetryFactory, NRetriesFactory, CircuitBreakerRetryFactory

drain = False

def net_rtt():
    return random.expovariate(1 / 0.01)

class Stats(object):
    def __init__(self, failure_rate, name):
        self.successes = 0
        self.total_calls = 0
        self.unique_calls = 0
        self.failure_rate = failure_rate
        self.name = name

    def first_try(self):
        self.unique_calls += 1
        self.total_calls += 1

    def retry(self):
        self.total_calls += 1

    def success(self):
        self.successes += 1

    def print(self):
        print("%f,%f,%f,%f,%s"%(self.failure_rate, self.successes, self.total_calls, self.unique_calls, self.name))

    def header():
        print("failure_rate,successes,total_calls,unique_calls,name")

class Client(object):
    def __init__(self, retry_strategy, rate_rps, server, stats):
        self.retry_strategy = retry_strategy
        self.rate = rate_rps
        self.server = server
        self.stats = stats

    def gen_load(self, _payload, t):
        call = Call(self.retry_strategy, self.server, self.stats)
        if drain:
            return [] 
        else: 
            return [(t + random.expovariate(self.rate), self.gen_load, None),
                    (t, call.start, None)]

class Call(object):
    def __init__(self, retry_strategy, server, stats):
        self.retry_strategy = retry_strategy.new_call()
        self.server = server
        self.stats = stats

    def start(self, _payload, t):
        self.retry_strategy.start()
        self.stats.first_try()
        return [(t + net_rtt(), self.server.handle, self)]
        

    def done_success(self, _payload, t):
        self.stats.success()
        return []

    def done_failure(self, _payload, t):
        if self.retry_strategy.should_retry():
            self.stats.retry()
            return [(t + net_rtt(), self.server.handle, self)]
        else:
            return []

class Server(object):
    def __init__(self, failure_rate):
        self.failure_rate = failure_rate

    def handle(self, call, t):
        if random.random() > self.failure_rate:
            return [(t + net_rtt(), call.done_success, None)]
        else:
            return [(t + net_rtt(), call.done_failure, None)]
        
def sim_loop(clients, max_t):
    global drain
    t = 0.0
    q = [(net_rtt(), client.gen_load, None) for client in clients]
    drain = False
    while len(q) > 0:
        (t, call, payload) = heapq.heappop(q)
        q.extend(call(payload, t))
        heapq.heapify(q)
        drain = t > max_t

def run_sims(max_t):
    n_clients = 100
    rate_per_client = 10.0

    Stats.header()
    for failure_rate in [0.0, 0.0001, 0.0002, 0.0005, 0.001, 0.002, 0.005, 0.01, 0.02, 0.0325, 0.05, 0.75, 0.1, 0.2, 0.3, 0.4, 0.5]:
        for name, retry_factory in [
                ("no_retries", NRetriesFactory(0)),
                ("three_retries", NRetriesFactory(3)),
                ("adaptive_10pct", AdaptiveRetryFactory(0.1, 5)),
                ("breaker_10pct", CircuitBreakerRetryFactory(NRetriesFactory(3), 0.1))]:
            stats = Stats(failure_rate, name)
            server = Server(failure_rate)
            clients = [ Client(retry_factory.make(), rate_per_client, server, stats) for client in range(n_clients)]
            sim_loop(clients, max_t)
            stats.print()

def run_sims_clients(max_t):
    rate = 1000.0

    Stats.header()
    for n_clients in [10, 100, 1000]:
        for failure_rate in [0.0, 0.0001, 0.0002, 0.0005, 0.001, 0.002, 0.005, 0.01, 0.02, 0.0325, 0.05, 0.75, 0.1, 0.2, 0.3, 0.4, 0.5]:
            for name, retry_factory in [
                ("adaptive_10pct_%dclients"%(n_clients), AdaptiveRetryFactory(0.1, 5)),
                ("breaker_10pct_%dclients"%(n_clients), CircuitBreakerRetryFactory(NRetriesFactory(3), 0.1))]:
                stats = Stats(failure_rate, name)
                server = Server(failure_rate)
                clients = [ Client(retry_factory.make(), rate/n_clients, server, stats) for client in range(n_clients)]
                sim_loop(clients, max_t)
                stats.print()

run_sims_clients(10.0)





    



