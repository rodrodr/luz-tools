# ERGM of the undirected co-signature network of one legislature (members who signed at least one
# measure), homophily terms as in the dyadic logit:
#   indep   edges + nodematch(party, family, district, region) + absdiff(ideology) + nodefactor(activity
#           tercile), fitted by MPLE: dyad-independent, a logit
#   gwesp   the same + gwesp(decay, fixed): triadic closure, MCMC maximum likelihood. Inference no
#           longer assumes independent dyads.
# Writes results/ergm_<model>_<leg>.csv (+ .rds, and for gwesp the MCMC diagnostics and GOF as PDF).
# Rscript analysis/inferencia_redes/03_ergm.R <legislature> <indep|gwesp> [decay] [seed]
source(file.path(dirname(normalizePath(sub("^--file=", "", grep("^--file=", commandArgs(FALSE), value = TRUE)))),
                 "common.R"))
suppressMessages({library(network); library(ergm)})

args <- commandArgs(TRUE)
leg <- args[1]
model <- args[2]
decay <- if (length(args) > 2) as.numeric(args[3]) else 0.5
seed <- if (length(args) > 3) as.integer(args[4]) else 1L

b <- build(leg, "active")
nodes <- b$nodes
ids <- as.character(nodes$id_dip)
ties <- b$dyads[b$dyads$tie == 1, ]
net <- network.initialize(length(ids), directed = FALSE)
pos <- setNames(seq_along(ids), ids)
add.edges(net, pos[as.character(ties$i)], pos[as.character(ties$j)])
for (a in c("party", "family", "district", "region", "ideo_pos")) set.vertex.attribute(net, a, nodes[[a]])
set.vertex.attribute(net, "tercile", as.character(nodes$tercile))

f_indep <- net ~ edges + nodematch("party") + nodematch("family") + nodematch("district") + nodematch("region") +
  absdiff("ideo_pos") + nodefactor("tercile", levels = c("mid", "high"))
t0 <- Sys.time()
if (model == "indep") {
  fit <- ergm(f_indep, estimate = "MPLE")
} else {
  f <- update(f_indep, ~ . + gwesp(decay, fixed = TRUE))
  fit <- ergm(f, control = control.ergm(seed = seed, MCMLE.maxit = 40, MCMC.burnin = 200000, MCMC.interval = 5000,
                                        MCMC.samplesize = 2000))
}
secs <- as.numeric(difftime(Sys.time(), t0, units = "secs"))
s <- summary(fit)$coefficients
res <- data.frame(legislature = leg, model = model, decay = if (model == "indep") NA else decay, term = rownames(s),
                  coef = s[, "Estimate"], se = s[, "Std. Error"], p = s[, "Pr(>|z|)"],
                  members = network.size(net), ties = network.edgecount(net), seconds = round(secs),
                  aic = tryCatch(as.numeric(AIC(fit))[1], error = function(e) NA), row.names = NULL)
tag <- if (model == "indep") sprintf("indep_%s", leg) else sprintf("gwesp%s_%s", decay, leg)
saveRDS(fit, file.path(ROOT, "results", sprintf("ergm_%s.rds", tag)))
write.csv(res, file.path(ROOT, "results", sprintf("ergm_%s.csv", tag)), row.names = FALSE)
print(res[, c("term", "coef", "se", "p")], digits = 4)
cat("seconds:", round(secs), "\n")
if (model != "indep") {
  pdf(file.path(ROOT, "results", sprintf("ergm_%s_mcmc.pdf", tag)))
  try(mcmc.diagnostics(fit))
  dev.off()
  g <- gof(fit, GOF = ~ degree + espartners + model, control = control.gof.ergm(nsim = 100, seed = seed))
  pdf(file.path(ROOT, "results", sprintf("ergm_%s_gof.pdf", tag)))
  plot(g)
  dev.off()
  capture.output(print(g), file = file.path(ROOT, "results", sprintf("ergm_%s_gof.txt", tag)))
}
