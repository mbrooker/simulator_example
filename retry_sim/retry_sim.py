import random
import heapq

from retry_strategy import AdaptiveRetryFactory, NRetriesFactory, CircuitBreakerRetryFactory
from client import Client, SerialClient, SerialClientWithBackoff, net_rtt

drain = False

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

class Server(object):
    def __init__(self, failure_rate):
        self.failure_rate = failure_rate

    def handle(self, call, t):
        if random.random() > self.failure_rate:
            return [(t + net_rtt(), call.done_success, None)]
        else:
            return [(t + net_rtt(), call.done_failure, None)]

def sim_loop(clients, max_t):
    t = 0.0
    q = [(net_rtt(), client.gen_load, None) for client in clients]
    drain = False
    while len(q) > 0:
        (t, call, payload) = heapq.heappop(q)
        q.extend(call(payload, t))
        heapq.heapify(q)
        # Simulation is over, tell the clients to stop sending work. This avoids a "right censoring" effect where we stop the sim with work in flight.
        if t > max_t and not drain:
            drain = True
            for c in clients:
                c.drain = True

# Simulation for "Simulating Performance" on https://brooker.co.za/blog/2022/02/28/retries.html
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
            clients = [ Client(retry_factory.make(), rate_per_client, server, stats, 0.0) for client in range(n_clients)]
            sim_loop(clients, max_t)
            stats.print()

# Simulation for "The effect of client count" on https://brooker.co.za/blog/2022/02/28/retries.html
def run_sims_clients(max_t):
    rate = 100.0

    Stats.header()
    for n_clients in [10, 100, 1000]:
        for failure_rate in [0.0, 0.0001, 0.0002, 0.0005, 0.001, 0.002, 0.005, 0.01, 0.02, 0.0325, 0.05, 0.75, 0.1, 0.2, 0.3, 0.4, 0.5]:
            for name, retry_factory in [
                ("adaptive_10pct_%dclients"%(n_clients), AdaptiveRetryFactory(0.1, 5)),
                ("breaker_10pct_%dclients"%(n_clients), CircuitBreakerRetryFactory(NRetriesFactory(3), 0.1))]:
                stats = Stats(failure_rate, name)
                server = Server(failure_rate)
                clients = [ Client(retry_factory.make(), rate/n_clients, server, stats, 0.0) for client in range(n_clients)]
                sim_loop(clients, max_t)
                stats.print()

def run_sims_retry_backoff(max_t):
    n_clients = 100
    rate_per_client = 10.0

    Stats.header()
    for failure_rate in [0.0, 0.0001, 0.0002, 0.0005, 0.001, 0.002, 0.005, 0.01, 0.02, 0.0325, 0.05, 0.75, 0.1, 0.2, 0.3, 0.4, 0.5]:
        for retry_backoff_name, retry_backoff in [("no", 0.0), ("large", 0.1)]:
            for name, retry_factory in [
                    ("three_retries_%s_backoff"%(retry_backoff_name), NRetriesFactory(3)),
                    ("adaptive_10pct_%s_backoff"%(retry_backoff_name), AdaptiveRetryFactory(0.1, 5))]:
                stats = Stats(failure_rate, name)
                server = Server(failure_rate)
                clients = [ Client(retry_factory.make(), rate_per_client, server, stats, retry_backoff) for client in range(n_clients)]
                sim_loop(clients, max_t)
                stats.print()

def run_sims_retry_serial(max_t):
    n_clients = 100
    rate_per_client = 10.0
    Stats.header()
    for failure_rate in [0.0, 0.0001, 0.0002, 0.0005, 0.001, 0.002, 0.005, 0.01, 0.02, 0.0325, 0.05, 0.75, 0.1, 0.2, 0.3, 0.4, 0.5]:
        for client_name, client_type in [("unbounded", Client), ("100_serial", SerialClient)]:
            for name, retry_factory in [
                    ("three_retries_%s"%(client_name), NRetriesFactory(3))]:
                stats = Stats(failure_rate, name)
                server = Server(failure_rate)
                clients = [ client_type(retry_factory.make(), rate_per_client, server, stats, 0.1) for client in range(n_clients)]
                sim_loop(clients, max_t)
                stats.print()

run_sims_retry_serial(10.0)





    



