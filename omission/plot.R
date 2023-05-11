library(ggplot2)
library(tidyverse)

width=6
height=3
dpi=100

plot_results <- function(name) {
	d = read.table(paste0(name, "_results.csv"), header=TRUE, sep=",")
	g = ggplot(d, aes(service_time)) + stat_ecdf(aes(color=name)) +
		ylab("Cumulative Density") +
		xlab("Client-Observed Latency")
	ggsave(paste0(name, "_ecdf.png"), dpi=dpi, width=width, height=height)

	g = ggplot(d, aes(service_time)) + stat_ecdf(aes(color=name)) +
		ylab("Cumulative Density") +
		xlab("Client-Observed Latency") +
		coord_cartesian(ylim = c(0.9, 1.0))
	ggsave(paste0(name, "_ecdf_zoomed.png"), dpi=dpi, width=width, height=height)

	gp = ggplot(d, aes(service_time)) + geom_freqpoly(aes(color=name),binwidth=1) + coord_cartesian(xlim = c(0,30)) + xlim(0,30)
	ggsave(paste0(name, "_pdf.png"), dpi=dpi, width=width, height=height)

	gq = ggplot(d, aes(x=t, y=qlen, color=name)) + geom_line() +
		ylab("Queue Length") +
		xlab("Time")
	ggsave(paste0(name, "_qlen.png"), dpi=dpi, width=width, height=height)
}

plot_results("exp")
plot_results("bimod")
plot_results("bimod_timeout")
plot_results("weibull")


# Print results for rho sweep
d = read.table("rho_sweep_results.csv", header=TRUE, sep=",")

g = ggplot(d, aes(service_time)) + stat_ecdf(aes(color=factor(rho))) +
		ylab("Cumulative Density") +
		xlab("Client-Observed Latency")

pctiles = d %>% group_by(rho) %>%  reframe(enframe(quantile(service_time, c(0.5, 0.9, 0.99, 0.999)), "quantile", "service_time"))

gp = ggplot(pctiles, aes(x=rho, y=service_time, color=quantile)) + geom_line() + geom_point()