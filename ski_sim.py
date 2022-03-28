# Example small numerical simulation, showing one way to simulate systems of queues and states.
#
# In this example, we're simulating the effects of different numbers of skiiers on the time that
#  skiiers spend waiting. This is particularly interesting because peak wait times can be super high,
#  even on days that aren't that much busier than usual.
#
# The core simulation is an event loop, with each event associated with a callback. When the callback is run,
#  it produces some more events that are added to the event loop. For efficiency, the event loop is implemented
#  as a heap, making it relatively efficient to get the next event.
#
# The goal of this code is to demonstrate the overall technique, and show how simple it can be to write your
# own event-based simulators. I intentionally don't use any libraries or frameworks here, although they can
# be useful. This code also isn't tuned for performance, 

import random
import heapq
from enum import Enum

# The arithmetic mean of the numbers in `l`
def avg(l):
    return sum(l)/float(len(l))

# Each skiier in our simulation is in one of three states: waiting for the lift, riding the lift, or skiing down a slope.
# The state machine couldn't be more straight forward:
#
#        +---------------------------------------------+       
#        |                                             |       
#        v                                             +       
# +-------------+        +-------------+        +-------------+
# |   Waiting   |------->| Riding Lift |------->|   Skiing    |
# +-------------+        +-------------+        +-------------+
#
class SkiierState(Enum):
    WAITING = 1
    RIDING_LIFT = 2
    SKIING = 3

# The `Skiier` class models each skiier in the simulation. A skiier has the following properties:
#  `speed`: The speed they ski down the slope at (in meters per second)
#  `lift`: A link back to the lift (and associated queue) they're going to ride when done skiing
#  `slope_len_m`: The length of the slope they're going to ski down (in meters)
class Skiier(object):
    def __init__(self, speed, lift, slope_len_m):
        self.speed = speed
        self.lift = lift
        self.slope_len_m = slope_len_m
        self.state = SkiierState.WAITING

    # Board the lift (after being in the queue)
    # Return an event for when this skiier will leave the lift
    def board_lift(self, t):
        assert self.state == SkiierState.WAITING
        self.state = SkiierState.RIDING_LIFT
        return [(t + self.lift.ride_time(), self.leave_lift, None)]
    
    # Get off the lift at the end of the lift ride, and start skiing
    # Return an event for when this skiier will get back to the lift line
    def leave_lift(self, _payload, t):
        assert self.state == SkiierState.RIDING_LIFT
        self.state = SkiierState.SKIING
        time_spent_skiing = self.slope_len_m / self.speed
        return [(t + time_spent_skiing, self.join_queue, None)]

    # Join the queue on our associated lift
    def join_queue(self, _payload, t):
        assert self.state == SkiierState.SKIING
        self.state = SkiierState.WAITING
        self.lift.queue.append(self)
        return None

# `Lift` models a ski lift and its associated queue.
# If you aren't familiar with chair lifts, start here: https://en.wikipedia.org/wiki/Chairlift
# The lift has the following attributes:
#  `ride_time` and `ride_time_stdev`: The mean and standard deviation of the time it takes to ride from boarding to departure
#  `chair_width`: The maximum number of skiiers who board the lift as each chair comes into the station
#  `chair_period`: How often chairs arrive (in seconds)
class Lift(object):
    def __init__(self, ride_time, ride_time_stdev, chair_width, chair_period):
        self.ride_time_mean = ride_time
        self.ride_time_stdev = ride_time_stdev
        self.chair_width = chair_width
        self.chair_period = chair_period
        # The queue of skiiers waiting to board starts empty
        self.queue = []

    # A chair has arrived. Board a number of skiiers onto the arriving chair, and set up their associated
    #  departure events.
    def dequeue_skiiers(self, _payload, t):
        events = [(t + self.chair_period, self.dequeue_skiiers, None)]
        for i in range(0, self.chair_width):
            if len(self.queue) > 0:
                skiier = self.queue.pop()
                events.extend(skiier.board_lift(t))
        return events

    # Return a single sample of the ride time distribution.
    # In reality, ride times aren't normal, and are highly correlated between all riders currently on the chair lift.
    # In a future simulation, we may explore the effect that this has one the overall dynamics.
    def ride_time(self):
        return random.normalvariate(self.ride_time_mean, self.ride_time_stdev)

# `Stats` is a simple object which runs periodically and writes down the current queue length, percentage of skiiers
#  currently skiing, and any other relevant information.
# When each simulation loop is complete, this object is used to report the results.    
class Stats(object):
    def __init__(self, name, lift, skiiers, calc_every):
        self.lift = lift
        self.skiiers = skiiers
        self.name = name
        self.calc_every = calc_every
        self.queue_lengths = []
        self.skiiers_skiing = []

    def calc_stats(self, _period, t):
        self.queue_lengths.append(len(self.lift.queue))
        n_skiiers_skiing = sum([ 1 if skiier.state == SkiierState.SKIING else 0 for skiier in self.skiiers])
        self.skiiers_skiing.append(n_skiiers_skiing / float(len(self.skiiers)))
        return [(t + self.calc_every, self.calc_stats, None)]

    def print(self):
        print("%f,%f,%d,%s"%(avg(self.queue_lengths), avg(self.skiiers_skiing), len(self.skiiers), self.name))

    def header():
        print("avg_queue_len,skiiers_skiing,skiiers,name")

# Run a single simulation.        
def sim_loop(max_t, stats, lift):
    t = 0.0
    q = [(0.0, stats.calc_stats, None), (random.random(), lift.dequeue_skiiers, None)]
    # This is the core simulation loop. Until we've reached the maximum simulation time, pull the next event off
    #  from a heap of events, fire whichever callback is associated with that event, and add any events it generates
    #  back to the heap.
    while len(q) > 0 and t < max_t:
        # Get the next event. Because `q` is a heap, we can just pop this off the front of the heap.
        (t, call, payload) = heapq.heappop(q)
        # Execute the callback associated with this event
        new_events = call(payload, t)
        # If the callback returned any follow-up events, add them to the event queue `q` and make sure its still a valid heap
        if new_events is not None:
            q.extend(new_events)
            heapq.heapify(q)

# Run a loop of simulations, for a range of parameters of interest.
#  In this case, we want to hold the parameters of the resort fixed, and vary the number of skiiers and the size of each chair on the lift line
def run_sims(max_t):
    # Chair parameters. These are roughly modelled on Crystal Mountain's Forest Queen chair.
    lift_ride_time = 300.0
    lift_ride_time_stdev = 30
    chair_period = 7.0
    slope_len_m = 3000.0
    # Skiier parameters. For now, these are just guesses. We could calibrate this will readl data (or even replace the statistical model with
    # one that samples from real measurements)
    mean_skiier_speed_mps = 5.0
    skiier_speed_stdev_mps = 1.0

    Stats.header()
    # Run the simulation for chairs that can hold 4 and 6 skiiers
    for chair_width in [4, 6]:
        name = "chair_%d_pack"%(chair_width)
        # And then for a range of skiers in the system
        for n_skiiers in range(25, 1250, 50):
            lift = Lift(lift_ride_time, lift_ride_time_stdev, chair_width, chair_period)
            # Each skiier is assigned a speed, using a normal distribution. In reality, skiier speed is unlikely to be normally distributed.
            #  How could we calibrate this model?
            skiiers = [Skiier(random.normalvariate(mean_skiier_speed_mps, skiier_speed_stdev_mps), lift, slope_len_m) for i in range(n_skiiers)]
            # All the skiiers start off in the lift queue at the beginning of the day. Clearly that's not realistic, but they have to start somewhere
            lift.queue = skiiers.copy()
            stats = Stats(name, lift, skiiers, 1.0)
            sim_loop(max_t, stats, lift)
            stats.print()

run_sims(50000.0)



