# PN Benchmark Report

## Overall Conclusion

**FAIL** — 1 failed case(s), 1 warning(s).

## Summary

| Field | Value |
|-------|-------|
| Run ID | `20260115_120000_a1b2c3d4` |
| Timestamp | 2026-01-15T12:00:00Z |
| Git Commit | `abc123d` |
| Total Cases | 5 |
| Passed | 2 |
| Warnings | 1 |
| Failed | 1 |
| Total Runtime | 12.45 s |

## Failed Cases

| Case | Failure Reason | Failed Checks |
|------|----------------|---------------|
| bad_tolerance | Metric Vbi rel error 30% exceeds tolerance 5% | Vbi, W, Emax |

## Warnings

| Case | Warning |
|------|---------|
| asymmetric_equilibrium | Solver reached max iterations but metrics within tolerance |

## Cases Without Analytic Validation

| Case | Mode | Validation Status | Reason | Outcome |
|------|------|-------------------|--------|---------|
| graded_junction | numerical_only | numerical_only | No abrupt analytic reference; frozen numerical reference used | pass |
| transient_step | validation_unavailable | unavailable | Analytic validation unavailable; behavioral checks only | pass |

## Recommendations

- Investigate 1 failed case(s): bad_tolerance
- Review warning cases for solver stability or relaxed tolerance drift
- Regenerate frozen reference metrics when graded/erfc physics or mesh changes

## Full Case Index

| Case | Model | Doping | Mode | Outcome | Solver | Validation | Run | Time (s) |
|------|-------|--------|------|---------|--------|------------|-----|---------:|
| symmetric_equilibrium | poisson | abrupt | analytic_abrupt | **pass** | converged | analytic_passed | completed | 1.23 |
| asymmetric_equilibrium | poisson | abrupt | analytic_abrupt | **warning** | max_iter_reached | analytic_passed | completed_with_warning | 2.87 |
| bad_tolerance | poisson | abrupt | analytic_abrupt | **fail** | converged | analytic_failed | failed | 1.05 |
| graded_junction | poisson | linear_graded | numerical_only | **pass** | converged | numerical_only | completed | 3.12 |
| transient_step | transient_dd | abrupt | validation_unavailable | **pass** | converged | unavailable | completed | 4.18 |
