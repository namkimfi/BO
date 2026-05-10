# -*- coding: utf-8 -*-
"""
MQDL 6-channel safe zeroing — stepwise ramp.

Ramps every MQDL channel (1..6) from its present voltage down to 0 V
in user-controlled small steps.  Deliberately does NOT use MQDL's
built-in `Z{ch}:50` (or `mqdl.zero()`) — those use a fixed 50-step
device-side ramp, while this script lets the experimenter set both
the per-step size and the dwell time.

Channels are zeroed one at a time, in numerical order (1 -> 6).
"""

import time
import pyvisa

from MQDLVoltageSource_v2 import MQDL


# =============================================================================
# 1. USER CONFIGURATION
# =============================================================================

MQDL_COM_PORT = 4                # MQDL serial COM number (integer)

RAMP_STEP  = 0.005   # V per step  (small = safer for the DUT)
RAMP_DELAY = 0.05    # s dwell between steps  (>= 0.05 to respect the 50 ms quiet-period rule)


# =============================================================================
# 2. helpers (same robust pattern as the measurement scripts)
# =============================================================================

def get_voltage_robust(mqdl, channel, retries=3, retry_delay=0.1):
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
    present = get_voltage_robust(mqdl, channel)
    sgn_step = abs(step) if present < target else -abs(step)
    while abs(present - target) > abs(sgn_step) / 2:
        new_v = present + sgn_step
        if (sgn_step > 0 and new_v > target) or (sgn_step < 0 and new_v < target):
            new_v = target
        mqdl.set(channel, new_v)
        time.sleep(delay)
        present = new_v
        print(f"  [zero{label}] ch{channel} -> {present:+.6f} V")
    mqdl.set(channel, target)
    time.sleep(delay)
    print(f"  [zero{label}] ch{channel} settled at {target:+.6f} V")


# =============================================================================
# 3. main
# =============================================================================

def main():
    assert RAMP_DELAY >= 0.05, "RAMP_DELAY must be >= 0.05 s (50 ms quiet-period rule)"

    rm = pyvisa.ResourceManager()
    print("Available VISA resources:", rm.list_resources())

    mqdl = MQDL(MQDL_COM_PORT)

    print("\nPresent channel voltages (read-back / cache):")
    for ch in range(1, 7):
        try:
            v = get_voltage_robust(mqdl, ch)
            print(f"  ch{ch}: {v:+.6f} V")
        except Exception as e:
            print(f"  ch{ch}: read failed ({e})")

    try:
        for ch in range(1, 7):
            print(f"\n--- ch{ch}: ramping to 0 V ---")
            stepwise_ramp(mqdl, ch, 0.0, RAMP_STEP, RAMP_DELAY, label=f" ch{ch}")
    finally:
        try:
            mqdl.inst.close()
        except Exception:
            pass

    print("\nAll channels are now at 0 V.")


if __name__ == "__main__":
    main()
