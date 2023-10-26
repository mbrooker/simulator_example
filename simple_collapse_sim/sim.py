# Simulate the behavior of a simple system consisting of a set of clients, and a server
#  with latency that depends on the number of concurrent requests it is processing.
# The goal of the simulator is to show that the simple combination of timeout and retry,
#  even with backoff, leads to unstable system behavior in open systems.
#
#                 ┌────────────┐                              
#                 │┌───────────┴┐       ┌────────────────────┐
#   Poisson       ││  Clients   │       │       Server       │
#   Arrival  ─────▶│  (retry 3  │──────▶│ (latency increase  │
#   Process       └┤   times)   │       │ with concurrency)  │
#                  └────────────┘       └────────────────────┘

import random
import heapq
from dataclasses import dataclass

network_delay = 0.1
max_request_t = 3.0
base_server_time = 1.0
server_concurrency_slope = 0.01

# Calculate the mean of an array of values
def avg(v):
    return sum(v) / len(v)

# Simulate a network delay between the client and the server
def netdelay(t):
    return t + random.expovariate(1.0/network_delay)

# Clients try to make a single request against the server. If that request doesn't succeed withing `max_request_t` they
#  retry it up to 3 times.
class Client(object):
    def __init__(self, stats, server):
        self.retries_left = 3
        self.current_try = 0
        self.server = server
        self.stats = stats

    # Send a request to the server, and set up the timeout
    def send_req(self, t, extra_delay):
        return [(t + max_request_t + extra_delay, self.timeout, (self.current_try,)),
            (netdelay(t) + extra_delay, self.server.start, (self, self.current_try))]
    
    def send_new_req(self, t):
        self.stats.start()
        return self.send_req(t, 0.0)
    
    # Amount of time to wait for a retry. This version doesn't wait, to simulate the case with no backoff or jitter.
    def retry_wait(self):
        return 0
    
    # Handle the timeout signal. The timeout signal is ignored if we've run out of retries, or if its a timeout
    #  from a previous attempt. 
    def timeout(self, t, data):
        if data[0] == self.current_try:
            self.stats.timeout()
            self.retries_left -= 1
            self.current_try += 1
            if self.retries_left > 0:
                self.stats.retry()
                return self.send_req(t, self.retry_wait())
            else:
                return None
    
    # Handle the server's response. The response is ignored if we've already timed out this attempt (which is the behavior
    #  implemented by most real-world clients).
    def done(self, t, data):
        if data[1] == self.current_try:
            self.stats.success()
            self.current_try += 1
            return None

# Implementation of client that implements exponential backoff and jitter        
class ClientWithBackoffAndJitter(Client):
    def __init__(self, stats, server):
        super().__init__(stats, server)
        self.backoff_time = 10.0

    # Retry wait with exponential backoff and Jitter
    def retry_wait(self):
        self.backoff_time *= 2
        return random.random() * self.backoff_time


# The server processes requests as they come in, sending a response after some delay.
# The delay is calculated with a simple linear model: some base response time, plus an additional time linear in the number
#  of in-flight requests.
# This is intended to (very roughly) simulate the cooordination and coherence costs that become more costly as concurrency increases.
class Server(object):
    def __init__(self):
        self.concurrency = 0

    def start(self, t, data):
        self.concurrency += 1
        return [(t + base_server_time + self.concurrency * server_concurrency_slope, self.end, data)]
    
    def end(self, t, data):
        self.concurrency -= 1
        return [(netdelay(t), data[0].done, data)]

# Generate a Poisson arrival process with a base rate that ramps up linearly to some peak, then ramps back down at the same rate
class RampUpDownLoadGenerator(object):
    def __init__(self, stats, server, client_type, base_rate, slope, peak_t):
        self.stats = stats
        self.server = server
        self.base_rate = base_rate
        self.slope = slope
        self.peak_t = peak_t
        self.client_type = client_type

    def gen_load(self, t, _data):
        rsp = self.client_type(self.stats, self.server).send_new_req(t)
        rate = self.base_rate - self.slope * abs(t - self.peak_t)
        if rate > 0:
            rsp.append((t + random.expovariate(rate), self.gen_load, None))
        return rsp
    
# Generate a Poisson arrival process that continues at a constant rate, spikes up to a new rate for a fixed time, then drops back down
class SpikeLoadGenerator(object):
    def __init__(self, stats, server, client_type, base_rate, peak_rate, spike_start, spike_width):
        self.stats = stats
        self.server = server
        self.base_rate = base_rate
        self.peak_rate = peak_rate
        self.spike_start = spike_start
        self.spike_width = spike_width
        self.client_type = client_type

    def gen_load(self, t, _data):
        rsp = self.client_type(self.stats, self.server).send_new_req(t)
        if t < self.spike_start or t > self.spike_start + self.spike_width:
            rsp.append((t + random.expovariate(self.base_rate), self.gen_load, None))
        else:
            rsp.append((t + random.expovariate(self.peak_rate), self.gen_load, None))
        return rsp

@dataclass
class StatData:
    start_t: float
    server: Server
    run_name: str
    starts: int = 0
    successes: int = 0
    retries: int = 0
    timeouts: int = 0

    def header():
        print("t, starts, successes, retries, timeouts, concurrency, run_name")

    def print_csv(self):
        print(f"{self.start_t},{self.starts},{self.successes},{self.retries},{self.timeouts},{self.server.concurrency},{self.run_name}")

def stat_data_average(stat_data_v):
    data = StatData(stat_data_v[0].start_t, stat_data_v[0].server, stat_data_v[0].run_name)
    data.starts = avg([stat_data.starts for stat_data in stat_data_v])
    data.successes = avg([stat_data.successes for stat_data in stat_data_v])
    data.retries = avg([stat_data.retries for stat_data in stat_data_v])
    data.timeouts = avg([stat_data.timeouts for stat_data in stat_data_v])
    return data

class Stats(object):
    def __init__(self, server,  run_name, print_out=False):
        self.data = StatData(0, server, run_name)
        self.history = []
        self.print_out = print_out

    def retry(self):
        self.data.retries += 1

    def start(self):
        self.data.starts += 1

    def success(self):
        self.data.successes += 1

    def timeout(self):
        self.data.timeouts += 1

    def print_stats(self, t, _data):
        self.history.append(self.data)
        if self.print_out:
            self.data.print_csv()
        self.data = StatData(t, self.data.server, self.data.run_name)
        return [(t + 1.0, self.print_stats, None)]

# Run the simulation with the RampUpDownLoadGenerator, which ramps up at a constant slope to a peak rate, then ramps back down
def run_sim_ramp(run_name, client_type):
    max_t = 80
    server = Server()
    stats = Stats(server, run_name)
    gen = RampUpDownLoadGenerator(stats, server, client_type, 80, 1.6, 25)
    q = [(1.0, stats.print_stats, None), (0.01, gen.gen_load, None)]
    sim_loop(max_t, q)
    return stats.history

# Run the simulation with the SpikeLoadGenerator, which has a constant rate, spikes up to a new rate, then drops back down
def run_sim_spike(run_name, client_type):
    max_t = 80
    server = Server()
    stats = Stats(server, run_name)
    gen = SpikeLoadGenerator(stats, server, client_type, 40, 80, 20, 5)
    q = [(1.0, stats.print_stats, None), (0.01, gen.gen_load, None)]
    sim_loop(max_t, q)
    return stats.history

# Run the same simulation `num_runs` times, and print out the average value at each stat point in each second
def run_multiple_and_average_stats(run_name, client_type, sim_fn, num_runs):
    stats = []
    for i in range(num_runs):
        for j, second_stat in enumerate(sim_fn(run_name, client_type)):
            if j >= len(stats):
                stats.append([])
            stats[j].append(second_stat)
    for data in stats:
        stat_data_average(data).print_csv()

# Run a single simulation.        
def sim_loop(max_t, q):
    t = 0.0
    heapq.heapify(q)
    # This is the core simulation loop. Until we've reached the maximum simulation time, pull the next event off
    #  from a heap of events, fire whichever callback is associated with that event, and add any events it generates
    #  back to the heap.
    while len(q) > 0 and t < max_t:
        # Get the next event. Because `q` is a heap, we can just pop this off the front of the heap.
        (t, call, payload) = heapq.heappop(q)
        #print(t)
        # Execute the callback associated with this event
        new_events = call(t, payload)
        # If the callback returned any follow-up events, add them to the event queue `q` and make sure its still a valid heap
        if new_events is not None:
            q.extend(new_events)
            heapq.heapify(q)

run_multiple_n = 10

StatData.header()
run_multiple_and_average_stats("ramp_no_backoff", Client, run_sim_ramp, run_multiple_n)
run_multiple_and_average_stats("ramp_backoff_and_jitter", ClientWithBackoffAndJitter, run_sim_ramp, run_multiple_n)

run_multiple_and_average_stats("spike_no_backoff", Client, run_sim_spike, run_multiple_n)
run_multiple_and_average_stats("spike_backoff_and_jitter", ClientWithBackoffAndJitter, run_sim_spike, run_multiple_n)