# Local build evidence

Measured on 2026-10-01, Python 3.12.10, Windows, CPU only.

- pytest: 50 passed.
- Installed pdr entry point ran fixtures, run and Markdown report in 0.689 seconds total, measured with time.perf_counter across three subprocesses. This is runtime, not time saved.
- 200 synthetic input records; 80 planted deadlines found; zero false positives; zero false negatives against the independent expectations file.
- Counts: 67 email, 67 file, 66 calendar; 120 records without detected deadlines.
- All detected IDs and dates were compared, not only aggregate counts.
- Removing one planted deadline changes the computed count to 79, covered by pytest. Changing expectations alone never controls the output.
- Five-record hand-written example produces three matches, covered by pytest.
- Saved demo output: evidence/demo-report.md. All its inputs are synthetic.
- Repeated fixture generation and repeated runs produce byte-identical bytes in tests. Reports omit clocks and timing.

Initial run: 45 tests passed and two failed. The CSV error naming and input/output directory boundary were corrected, with regression coverage retained. Final suite: 50 passed.

Real use, real accuracy, time saved, money saved and two-week usage are unmeasured. The final project verdict awaits the actual evidence window in VERDICT.md. No external service or publishing step was used.
