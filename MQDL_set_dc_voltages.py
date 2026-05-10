# -*- coding: utf-8 -*-
"""
MQDL 6-channel DC voltage setter — stepwise ramp.

Sets user-specified DC voltages on any subset of MQDL channels.
Every channel move is performed step-by-step in Python (NOT via the
MQDL R command), so the experimenter controls the per-step size and
dwell time.  Channels are ramped one at a time, in the order given
in TARGETS, to avoid surprising transient combinations of voltages
on the DUT during the ramp.
"""

import time
import pyvisa

from MQDLVoltageSource_v2 import MQDL


# =============================================================================
# 1. USER CONFIGURATION
# =============================================================================

MQDL_COM_PORT = 4                # MQDL serial COM number (integer)

# Target voltage (V) for each channel.
#   - a number       -> ramp this channel from its present voltage to that target
#   - None           -> leave this channel alone (no ramp, no command)
# Channels are processed in the order they appear below; reorder for safety.
TARGETS = {
    1: 0.5,
    2: -0.3,
    3: 0.0,
    4: None,
    5: 0.2,
    6: -0.1,
}

# Stepwise-ramp parameters (apply to every channel).
RAMP_STEP  = 0.005   # V per step  (small = safer for the DUT)
RAMP_DELAY = 0.05    # s dwell between steps  (>= 0.05 to respect the 50 ms quiet-period rule)


# =============================================================================
# 2. helpers
# =============================================================================

def get_voltage_robust(mqdl, channel, retries=3, retry_delay=0.1):
    """Read MQDL channel voltage with retries; fall back to v2 cache."""
    last_err = None
    for _ in range(retries):
        try:
            _, vals = mqdl.get_value(channel)
            return float(vals[0])
        except (ValueError, TypeError) as e:
            last_err = e
            time.sleep(retry_delay)
    cached = getattr(mqdl, "_channel_cache", {}).get(channel)
    if cached is not None:
        try:
            return float(cached)
        except (TypeError, ValueError):
            pass
    raise RuntimeError(
        f"ch{channel} read-back failed after {retries} retries: {last_err}"
    )


def stepwise_ramp(mqdl, channel, target, step, delay, label=""):
    """Move MQDL `channel` from its present voltage to `target` in safe
    steps of size `step` V, waiting `delay` s between each set.

    Tracks the COMMANDED voltage (no read-back inside the loop) — the
    MQDL firmware can return malformed replies if queried while still
    processing a recent set.
    """
    present = get_voltage_robust(mqdl, channel)
    sgn_step = abs(step) if present < target else -abs(step)
    while abs(present - target) > abs(sgn_step) / 2:
        new_v = present + sgn_step
        if (sgn_step > 0 and new_v > target) or (sgn_step < 0 and new_v < target):
            new_v = target
        mqdl.set(channel, new_v)
        time.sleep(delay)
        present = new_v
        print(f"  [ramp{label}] ch{channel} -> {present:+.6f} V")
    mqdl.set(channel, target)
    time.sleep(delay)
    print(f"  [ramp{label}] ch{channel} settled at {target:+.6f} V")


# =============================================================================
# 3. main
# =============================================================================

def main():
    # ---- sanity checks ----
    for ch in TARGETS:
        assert 1 <= ch <= 6, f"MQDL channel {ch} out of range 1..6"
    assert RAMP_DELAY >= 0.05, "RAMP_DELAY must be >= 0.05 s (50 ms quiet-period rule)"

    # ---- show available resources & plan ----
    rm = pyvisa.ResourceManager()
    print("Available VISA resources:", rm.list_resources())
    print("\nPlan (in this order):")
    for ch, target in TARGETS.items():
        if target is None:
            print(f"  ch{ch}: leave alone")
        else:
            print(f"  ch{ch}: ramp to {target:+.6f} V")

    # ---- open MQDL ----
    mqdl = MQDL(MQDL_COM_PORT)

    try:
        for ch, target in TARGETS.items():
            if target is None:
                print(f"\n--- ch{ch}: skipped ---")
                continue
            print(f"\n--- ch{ch}: ramping to {target:+.6f} V ---")
            stepwise_ramp(mqdl, ch, float(target), RAMP_STEP, RAMP_DELAY,
                          label=f" ch{ch}")
    finally:
        # Release the COM port handle so the next session does not hit
        # VI_ERROR_RSRC_BUSY.  Channels are NOT zeroed here — this script's
        # purpose is to set DC voltages and leave them on.
        try:
            mqdl.inst.close()
        except Exception:
            pass

    print("\nDone.  Channel voltages are now:")
    # report final state (commanded values from cache)
    for ch in range(1, 7):
        v = mqdl._channel_cache.get(ch)
        if v is None or not isinstance(v, (int, float)):
            print(f"  ch{ch}: unknown")
        else:
            print(f"  ch{ch}: {v:+.6f} V")


if __name__ == "__main__":
    main()
