# Small simulator that plots the ratio between the mean and 99th percentile load on a fleet of machines with a varying number of
#  independent loads.
#
# Don't take this as a good example of R code.
library(ggplot2)
library(reshape2)

# Given the random number generator rf, estimate the mean-to-`pctile` ratio of the sum of `N` random numbers, with `runs` samples.
pctile_of_N <- function(rf, pctile, N, runs) {
	return(sapply(N, 
		function(n) {
			 samples <- sapply(1:runs, function(a) { return(sum(rf(n))) })
			 return(mean(samples) / quantile(samples, pctile))
		}
	 ))
}

# Return a function which generates Weibull-distributed numbers with mean 1 and shape `shape`
m1_weibull <- function(shape) {
	# Calculate the scale needed to get a mean of 1 for `shape`
	scale <- 1/gamma(1 + 1 / shape)
	return(function(N) { rweibull(N, shape, scale) })
}

x <- (200*(1:500))**0.4
pctile <- 0.99
runs <- 10000

t <- data.frame(x=x,
	weibull_2=pctile_of_N(m1_weibull(2), pctile, x, runs),
	weibull_3=pctile_of_N(m1_weibull(3), pctile, x, runs),
	weibull_4=pctile_of_N(m1_weibull(4), pctile, x, runs),
	exponential=pctile_of_N(rexp, pctile, x, runs))

tm <- melt(t, id.vars=c('x'))

g <- ggplot(tm, aes(x=x, y=value, color=variable)) +
	 geom_point() +
	 scale_x_sqrt() +
	 xlab("Number of Tenants") +
	 ylab("Fleet mean / 99th percentile") +
	 guides(color=guide_legend(title="Per-Tenant Distrib."))

ggsave("fleet_stat.png", dpi=100, width=5, height=3)