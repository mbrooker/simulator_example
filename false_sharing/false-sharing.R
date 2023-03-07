# Estimate the effects of sharding on zipf-distributed and uniform distributed rows, to illustrate the effect of "false sharing"
#  The distribution is estimated using a bootstrap method, where we take the weights of each Zipf sample,
#   shuffle them, and then sum up slices of the weights.

# Read about it at https://brooker.co.za/blog/2023/03/07/false-sharing.html
library(ggplot2)
library(reshape2)
# For `dzipf`, `rzipf`, and `zeta` functions
library(VGAM)
# for hue_pal()
library(scales)

width=5
height=2.5
dpi=120

sample_f <- function(dist_d, shards) {
	r_dist_d = sample(dist_d)[1:(shards*floor(length(dist_d)/shards))]
	grouped = rowSums(matrix(r_dist_d, nrow=shards))
	return(max(grouped))
}

sample_f_multiple_zipf <- function(N, shards, runs, shape) {
	zipf_d = dzipf(1:N, N, shape)
	return(sapply(1:runs, function(x) sample_f(zipf_d, shards)))
}

sample_f_multiple_unif <- function(N, shards, runs, shape) {
	unif_d = runif(N)
	# Normalize to a sum of 1, so each row gets a uniform weight with the total weight being 1
	unif_d = unif_d / sum(unif_d)
	return(sapply(1:runs, function(x) sample_f(unif_d, shards)))
}

shape = 1.2
N=10000
runs = 50000
pal = hue_pal()(4)

d = data.frame(s2=sample_f_multiple_zipf(N, 2, runs, shape), s5=sample_f_multiple_zipf(N, 5, runs, shape), s10=sample_f_multiple_zipf(N, 10, runs, shape))
dm = melt(d)

g = ggplot(dm, aes(value, color=variable)) + stat_ecdf() +
	geom_vline(xintercept=1/2, color=pal[1], linetype="dashed") +
	geom_vline(xintercept=1/5, color=pal[2], linetype="dashed") +
	geom_vline(xintercept=1/10, color=pal[3], linetype="dashed") +
	guides(color=guide_legend(title="shards")) +
	ylab("Culumative Density") +
	xlab("Heat of Hottest Shard")
ggsave("zipf_false_sharing.png", dpi=dpi, width=width, height=height)

gp = ggplot(dm, aes(value, color=variable)) + geom_freqpoly() +
	ylab("Count") +
	xlab("Hottest Shard Heat") +
	guides(color=guide_legend(title="shards")) +
	geom_vline(xintercept=1/2, color=pal[1], linetype="dashed") +
	geom_vline(xintercept=1/5, color=pal[2], linetype="dashed") +
	geom_vline(xintercept=1/10, color=pal[3], linetype="dashed")
ggsave("zipf_false_sharing_pdf.png", dpi=dpi, width=width, height=height)

d = data.frame(s2=sample_f_multiple_unif(N, 2, runs, shape), s5=sample_f_multiple_unif(N, 5, runs, shape), s10=sample_f_multiple_unif(N, 10, runs, shape))
dm = melt(d)
g = ggplot(dm, aes(value, color=variable)) + stat_ecdf() +
	geom_vline(xintercept=1/2, color=pal[1], linetype="dashed") +
	geom_vline(xintercept=1/5, color=pal[2], linetype="dashed") +
	geom_vline(xintercept=1/10, color=pal[3], linetype="dashed") +
	guides(color=guide_legend(title="shards")) +
	ylab("Culumative Density") +
	xlab("Heat of Hottest Shard")
ggsave("unif_false_sharing.png", dpi=dpi, width=width, height=height)

gp = ggplot(dm, aes(value, color=variable)) + geom_freqpoly() +
	ylab("Count") +
	xlab("Hottest Shard Heat") +
	guides(color=guide_legend(title="shards")) +
	geom_vline(xintercept=1/2, color=pal[1], linetype="dashed") +
	geom_vline(xintercept=1/5, color=pal[2], linetype="dashed") +
	geom_vline(xintercept=1/10, color=pal[3], linetype="dashed")
ggsave("unif_false_sharing_pdf.png", dpi=dpi, width=width, height=height)