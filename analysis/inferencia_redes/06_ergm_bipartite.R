# Two-mode ERGM: deputies (first mode) × measures (second mode), one tie per identified signature.
# The co-signature network is the projection of this one: every measure becomes a clique, which
# makes a one-mode ERGM with triadic closure near-degenerate. Here homophily is b1nodematch: do
# deputies who share party, family, district, region or ideology sign the same measures more than
# chance? Both degree sequences are held fixed (constraints = ~ degrees): every deputy keeps the
# number of measures they signed and every measure its number of signatories, so activity and
# measure size are controlled exactly and only who signs with whom can vary. (Modelling them with
# gwb1degree/gwb2degree instead degenerates.) beta = 0.5 discounts the two-paths of each tie
# (Bomiriya, Bansal and Hunter 2023, arXiv:2312.05673).
# Measures with fewer than two identified signatories carry no co-signature and are left out.
# With a fourth argument "dsp" the model adds gwb1dsp(0.5, fixed): repeated collaboration, pairs of
# deputies who share many measures (the base model leaves too few of them, see the GOF).
# Rscript analysis/inferencia_redes/06_ergm_bipartite.R <legislature> [beta] [seed] [dsp]
source(file.path(dirname(normalizePath(sub("^--file=", "", grep("^--file=", commandArgs(FALSE), value = TRUE)))),
                 "common.R"))
suppressMessages({library(network); library(ergm)})

args <- commandArgs(TRUE)
leg <- args[1]
beta <- if (length(args) > 1) as.numeric(args[2]) else 0.5
seed <- if (length(args) > 2) as.integer(args[3]) else 1L
dsp <- length(args) > 3 && args[4] == "dsp"

sig <- read.csv(file.path(ROOT, "data", sprintf("signatures_%s.csv", leg)))
size <- table(sig$id_medida)
sig <- sig[sig$id_medida %in% as.integer(names(size)[size >= 2]), ]
nodes <- read.csv(file.path(ROOT, "data", sprintf("nodes_%s.csv", leg)), stringsAsFactors = FALSE)
deps <- sort(unique(sig$id_dip)); meas <- sort(unique(sig$id_medida))
nd <- length(deps)
net <- network.initialize(nd + length(meas), directed = FALSE, bipartite = nd)
add.edges(net, match(sig$id_dip, deps), nd + match(sig$id_medida, meas))
a <- nodes[match(deps, nodes$id_dip), ]
for (k in c("party", "family", "district", "region", "ideology"))
  set.vertex.attribute(net, k, c(a[[k]], rep(NA, length(meas))))

f <- net ~ b1nodematch("party", beta = beta) + b1nodematch("family", beta = beta) +
  b1nodematch("district", beta = beta) + b1nodematch("region", beta = beta) + b1nodematch("ideology", beta = beta)
if (dsp) f <- update(f, ~ . + gwb1dsp(0.5, fixed = TRUE))
t0 <- Sys.time()
fit <- ergm(f, constraints = ~ degrees,
            control = control.ergm(seed = seed, MCMLE.maxit = 40, MCMC.burnin = 200000, MCMC.interval = 5000,
                                   MCMC.samplesize = 2000))
secs <- as.numeric(difftime(Sys.time(), t0, units = "secs"))
s <- summary(fit)$coefficients
res <- data.frame(legislature = leg, model = if (dsp) "bipartite_dsp" else "bipartite", beta = beta, term = rownames(s), coef = s[, "Estimate"],
                  se = s[, "Std. Error"], p = s[, "Pr(>|z|)"], deputies = nd, measures = length(meas),
                  signatures = nrow(sig), seconds = round(secs), row.names = NULL)
tag <- sprintf("bipartite%s_b%s_%s", if (dsp) "_dsp" else "", beta, leg)
saveRDS(fit, file.path(ROOT, "results", sprintf("ergm_%s.rds", tag)))
write.csv(res, file.path(ROOT, "results", sprintf("ergm_%s.csv", tag)), row.names = FALSE)
print(res[, c("term", "coef", "se", "p")], digits = 4)
cat("seconds:", round(secs), "\n")
pdf(file.path(ROOT, "results", sprintf("ergm_%s_mcmc.pdf", tag)))
try(mcmc.diagnostics(fit))
dev.off()
g <- gof(fit, GOF = ~ b1dsp(0:15) + model, control = control.gof.ergm(nsim = 100, seed = seed))  # degrees are fixed
pdf(file.path(ROOT, "results", sprintf("ergm_%s_gof.pdf", tag)))
plot(g)
dev.off()
capture.output(print(g), file = file.path(ROOT, "results", sprintf("ergm_%s_gof.txt", tag)))
