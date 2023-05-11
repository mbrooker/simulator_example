# Small simulator for measuring the difference between open-loop and closed-loop client-observed latency in a G/G/c queuing system.
# Created for the blog post https://brooker.co.za/blog/2023/05/10/open-closed.html
import random
import heapq
import math
from collections import deque

# Convert from a mean and shape to the 'scale' parameter that Python's weibullvariate expects
def weibull_scale(mean, shape):
    return mean/math.gamma(1.0 + 1.0 / shape)

# Job with unimodal exponentially distributed latency
def exp_job(mean):
    class ExpJob(object):
        def __init__(self, t):
            self.created_t = t
            self.size = random.expovariate(1.0 / mean)
        def mean():
            return mean
    return ExpJob

# Job with bimodal exponentially distributed latency
def bimod_job(mean_1, mean_2, p):
    class BiModJob(object):
        def __init__(self, t):
            self.created_t = t
            if random.random() > p:
                self.size = random.expovariate(1.0 / mean_1)
            else:
                self.size = random.expovariate(1.0 / mean_2)
        def mean():
            return (1.0 - p)*mean_1 + p*mean_2
    return BiModJob

# Job with Weibull-distributed latency
def weibull_job(mean, shape):
    class WeibullJob(object):
        def __init__(self, t):
            self.created_t = t
            self.size = random.weibullvariate(weibull_scale(mean, shape), shape)
        def mean():
            return mean
    return WeibullJob

# First-Come-First-Served Queue
class FCFSQueue(object):
    def __init__(self):
        self.deque = deque()

    def append(self, job):
        self.deque.append(job)

    def pop(self):
        return self.deque.popleft()

    def len(self):
        return len(self.deque)

    def name(self):
        return "FCFS"

# Server that consumes a queue of tasks, with a fixed concurrency (MPL)
class Server(object):
    def __init__(self, mpl, sim_name, client, rho):
        self.busy = 0
        self.queue = FCFSQueue()
        self.sim_name = sim_name
        self.mpl = mpl
        self.jobs = [ None for i in range(mpl) ]
        self.client = client
        self.rho = rho

    def job_done(self, t, n):
        assert(self.busy > 0)
        completed = self.jobs[n]
        self.file.write("%f,%f,%f,%s,%d\n"%(t, self.rho, t - completed.created_t,  self.sim_name, self.queue.len()))

        events = []
        if self.queue.len() > 0:
            next_job = self.queue.pop()
            self.jobs[n] = next_job
            events = [(t + next_job.size, self.job_done, n)]
        else:
            self.busy -= 1
            self.jobs[n] = None
            
        done_event = self.client.done(t, completed)
        if done_event is not None:
            events.append(done_event)

        return events

    def offer(self, job, t):
        if self.busy < self.mpl:
            # The server isn't entirely busy, so we can start on the job immediately
            self.busy += 1
            for i in range(self.mpl):
                if self.jobs[i] is None:
                    self.jobs[i] = job
                    return (t + job.size, self.job_done, i)
            # Should never get here because jobs slots should always be available if busy < mpl
            assert(False)
        else:
            # The server is busy, so enqueue the job
            self.queue.append(job)
            return None

# Open loop load generation client. Creates an unbounded concurrency
class OpenLoopClient(object):
    def __init__(self, rho, job_type):
        self.rate_tps = rho / job_type.mean()
        self.job_type = job_type

    def generate(self, t, _payload):
        job = self.job_type(t)
        next_t = t + random.expovariate(self.rate_tps)
        offered = self.server.offer(job, t)
        if offered is None:
            return [(next_t, self.generate, None)]
        else:
            return [(next_t, self.generate, None), offered]

    def done(self, t, _event):
        return None

# Closed loop load generation client. Creates a fixed concurrency
class ClosedLoopClient(object):
    def __init__(self, rho, job_type, mpl):
        self.job_type = job_type
        self.mpl = mpl
        self.think_t = (1.0 - rho) * job_type.mean()
        self.think_t += (mpl - 1.0) * job_type.mean() / rho

    def generate(self, t, _payload):
        offers = [ self.server.offer(self.job_type(t), t) for i in range(self.mpl) ]
        return [ o for o in offers if o is not None ]

    def think_done(self, t, _payload):
        offer_rsp = self.server.offer(self.job_type(t), t)
        return [offer_rsp] if offer_rsp is not None else None

    def done(self, t, _event):
        return (t + random.expovariate(1.0/self.think_t), self.think_done, None)

# Open loop load generation client. Creates an unbounded concurrency
class OpenLoopClientWithTimeout(object):
    def __init__(self, rho, job_type, timeout):
        self.rate_tps = rho / job_type.mean()
        self.job_type = job_type
        self.timeout = timeout

    def generate(self, t, _payload):
        job = self.job_type(t)
        next_t = t + random.expovariate(self.rate_tps)
        offered = self.server.offer(job, t)
        if offered is None:
            return [(next_t, self.generate, None)]
        else:
            return [(next_t, self.generate, None), offered]

    def done(self, t, event):
        if t - event.created_t > self.timeout:
            # Offer another job as a replacement for the timed-out one
            return self.server.offer(self.job_type(t), t)
        else:
            return None


# Run a single simulation.        
def sim_loop(max_t, client):
    t = 0.0
    q = [(t, client.generate, None)]
    # This is the core simulation loop. Until we've reached the maximum simulation time, pull the next event off
    #  from a heap of events, fire whichever callback is associated with that event, and add any events it generates
    #  back to the heap.
    while len(q) > 0 and t < max_t:
        # Get the next event. Because `q` is a heap, we can just pop this off the front of the heap.
        (t, call, payload) = heapq.heappop(q)
        # Execute the callback associated with this event
        new_events = call(t, payload)
        # If the callback returned any follow-up events, add them to the event queue `q` and make sure its still a valid heap
        if new_events is not None:
            q.extend(new_events)
            heapq.heapify(q)

# Run a simulation, outputting the results to `fn`. One simulation is run for each client in `clients`.
#  `max_t` is the maximum time to run the simulation.
def run_sims(max_t, clients, fn):
    print("Running sim")
    with open(fn, "w") as f:
        f.write("t,rho,service_time,name,qlen\n")
        for client in clients:
            client.server.file = f
            sim_loop(max_t, client)

# Simulation with unimodal exponential service time
def make_sim_exp():
    mean_t = 0.1
    rho = 0.8
    clients = []
    job_name = "exp"
    job_type =  exp_job(mean_t)
    
    for name, client in [
        ("%s_open"%(job_name), OpenLoopClient(rho, job_type)),
        ("%s_closed_1"%(job_name), ClosedLoopClient(rho, job_type, 1)),
        ("%s_closed_10"%(job_name), ClosedLoopClient(rho, job_type, 10))]:
        server = Server(1, name, client, rho)
        client.server = server
        clients.append(client)
    return clients

# Simulation with bimodal service time (two exponential distributions)
def make_sim_bimod():
    mean_t = 0.1
    mean_t_2 = 10.0
    bimod_p = 0.001
    rho = 0.8
    clients = []
    job_name = "bimod"
    job_type =  bimod_job(mean_t, mean_t_2, bimod_p)
    
    for name, client in [
        ("%s_open"%(job_name), OpenLoopClient(rho, job_type)),
        ("%s_closed_1"%(job_name), ClosedLoopClient(rho, job_type, 1)),
        ("%s_closed_10"%(job_name), ClosedLoopClient(rho, job_type, 10))]:
        server = Server(1, name, client, rho)
        client.server = server
        clients.append(client)
    return clients

# Simulation with bimodal service time, with timeout
def make_sim_bimod_timeout():
    mean_t = 0.1
    mean_t_2 = 10.0
    bimod_p = 0.001
    timeout_t = 15.0
    rho = 0.8
    clients = []
    job_name = "open"
    job_type =  bimod_job(mean_t, mean_t_2, bimod_p)
    
    for name, client in [
        ("%s"%(job_name), OpenLoopClient(rho, job_type)),
        ("%s_timeout_%d"%(job_name, int(timeout_t)), OpenLoopClientWithTimeout(rho, job_type, timeout_t))]:
        server = Server(1, name, client, rho)
        client.server = server
        clients.append(client)
    return clients

# Simulation with Weibull service time
def make_sim_weibull():
    mean_t = 0.1
    shape = 2.0
    rho = 0.8
    clients = []
    job_name = "weibull"
    job_type =  weibull_job(mean_t, shape)
    
    for name, client in [
        ("%s_open"%(job_name), OpenLoopClient(rho, job_type)),
        ("%s_closed_1"%(job_name), ClosedLoopClient(rho, job_type, 1)),
        ("%s_closed_10"%(job_name), ClosedLoopClient(rho, job_type, 10))]:
        server = Server(1, name, client, rho)
        client.server = server
        clients.append(client)
    return clients

# Sweep over a range of `rho` values, and run a simulation for each value.
def weibull_rho_sweep():
    name = "rho_sweep"
    clients = []
    for rho_i in range(1, 10):
        rho = rho_i / 10.0
        client = OpenLoopClient(rho, weibull_job(0.1, 2.0))
        client.server = Server(1, name, client, rho)
        clients.append(client)
    return clients
        
run_t = 5000.0
run_sims(run_t, make_sim_bimod_timeout(), "bimod_timeout_results.csv")
run_sims(run_t, make_sim_exp(), "exp_results.csv")
run_sims(run_t, make_sim_bimod(), "bimod_results.csv")
run_sims(run_t, make_sim_weibull(), "weibull_results.csv")
run_sims(20000, weibull_rho_sweep(), "rho_sweep_results.csv")
