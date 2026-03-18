def intensive_task(work_units: int) -> int:
    """
    CPU-bound workload that avoids big-int growth.

    Runs a fixed-width integer mixing loop (64-bit) for `work_units` iterations.
    """
    # Xorshift-style mixing + LCG step, masked to 64-bit to stay bounded.
    x = 0x9E3779B97F4A7C15  # golden ratio odd constant
    mask = (1 << 64) - 1
    wu = int(work_units)
    for i in range(wu):
        x ^= (x >> 12) & mask
        x ^= (x << 25) & mask
        x ^= (x >> 27) & mask
        x = (x * 0x2545F4914F6CDD1D + i) & mask
    return x

