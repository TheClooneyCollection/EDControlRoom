import gc

# The suite builds hundreds of short-lived apps; at the default thresholds GC scans cost ~40ms per run.
gc.set_threshold(50_000, 20, 100)
