library(ggplot2)
library(ggpubr)

d = read.table("results.csv", header=TRUE, sep=",")

ggsuccess = ggplot(d, aes(x=100*failure_rate, y=100*successes/unique_calls, color=name)) + geom_line() + ylab("Successful Operations (%)") + xlab("Server-side failure rate (%)") + guides(color=guide_legend(title="Retry Strategy"))

ggload = ggplot(d, aes(x=100*failure_rate, y=100*total_calls/unique_calls, color=name)) + geom_line() + ylab("Load (%)") + xlab("Server-side failure rate (%)") + guides(color=guide_legend(title="Retry Strategy"))

g = ggarrange(ggsuccess, ggload, ncol=1, nrow=2)

ggsave("retry_simulation_results.png", dpi=100, width=5.4, height=6)

ggsuccessz = ggplot(d, aes(x=100*failure_rate, y=100*successes/unique_calls, color=name)) + geom_line() + ylab("Successful Operations (%)") + xlab("Server-side failure rate (%)") + xlim(0, 10) + ylim(80, 100) + guides(color=guide_legend(title="Retry Strategy"))

ggloadz = ggplot(d, aes(x=100*failure_rate, y=100*total_calls/unique_calls, color=name)) + geom_line() + ylab("Load (%)") + xlab("Server-side failure rate (%)") + xlim(0, 10) + ylim(100, 120) + guides(color=guide_legend(title="Retry Strategy"))

gz = ggarrange(ggsuccessz, ggloadz, ncol=1, nrow=2)

ggsave("retry_simulation_results_zoomed.png", dpi=100, width=5.4, height=6)

