# Lessons for KOML

The planted evaluation validates deterministic extraction of explicit ISO dates across normalized email, file and calendar records. It does not validate interpreting raw inbox prose. The domain needs a distinction between a date mention and a deadline: incidental and negated dates are negative cases, not obligations.

The assumption that all dates in messages are actionable was rejected by the fixture's 80 incidental and negated date cases. The implementation therefore requires an explicit field or a standalone approved phrase. This conservative choice has a known cost: prose deadlines and relative dates are missed until Henry normalizes them. Real-world recall remains unmeasured.

Evidence-based build improvement: the initial test run exposed unnamed CSV parser errors and result files accidentally placed inside the input directory. The corrected adapter names CSV failures and the CLI rejects run outputs inside input directories. Regression tests retain these cases.

Operating rule: establish independent labelled positives and negatives before implementation, preserve record-level evidence in outputs, and never generalize synthetic success into a claim about real-life accuracy.
