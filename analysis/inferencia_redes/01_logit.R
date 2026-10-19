# 1. glm on the tool's specification: must reproduce homophily()'s IRLS (results/tool_<leg>.json)
# 2. glm on the inference specification (active members), the naive baseline for MRQAP and ERGM
# Rscript analysis/inferencia_redes/01_logit.R
source(file.path(dirname(normalizePath(sub("^--file=", "", grep("^--file=", commandArgs(FALSE), value = TRUE)))),
                 "common.R"))

out <- list()
for (leg in LEGS) {
  for (spec in c("tool", "active")) {
    b <- build(leg, spec)
    m <- glm(formula_dyadic(b), family = binomial, data = b$dyads)
    s <- summary(m)$coefficients
    term <- sub("^activity_pair", "activity ", rownames(s))
    term[term == "(Intercept)"] <- "intercept"
    out[[length(out) + 1]] <- data.frame(legislature = leg, spec = spec, term = term, coef = s[, 1], se = s[, 2],
                                         p = s[, 4], members = nrow(b$nodes), dyads = nrow(b$dyads),
                                         ties = sum(b$dyads$tie), row.names = NULL)
  }
}
res <- do.call(rbind, out)
write.csv(res, file.path(ROOT, "results", "glm.csv"), row.names = FALSE)
print(res[res$spec == "active", c("legislature", "term", "coef", "se", "p", "members", "dyads")], digits = 4)
