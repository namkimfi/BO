# -*- coding: utf-8 -*-
"""
I - V_scan - V_step  at  V_fixed     (single-source MQDL version)

Ported from: QMT_spyder_ivvg_windup_v3_muxswitch_Pump1.py
Voltage source : MQDL 6-channel only (no Yokogawa).
Readout        : Keithley 2000 DMM, reading the VOLTAGE output of a
                 current preamplifier (Ithaco-style, gain in A/V).
Safety         : every voltage move is performed step-by-step in Python
                 (NOT using MQDL's built-in R ramp), so the experimenter
                 controls the per-step size and dwell time.
"""

import time
import re
import datetime
import numpy as np
import matplotlib.pyplot as plt
import pyvisa

from MQDLVoltageSource_v2 import MQDL


# =============================================================================
# 1. USER CONFIGURATION  --  edit this block before running
# =============================================================================

# ----- instrument addresses -----
# Per the original SOURCE.py (lab convention), MQDL takes the COM port
# number as a plain integer; SOURCE builds 'ASRL{n}::INSTR' internally.
MQDL_COM_PORT = 4                   # MQDL serial port number  (was COM4)
DMM_ADDRESS   = "GPIB43::19::INSTR"  # Keithley 2000

# ----- MQDL channel assignment (1..6) -----
# Choose any 3 distinct channels for the three roles.
CH_SCAN  = 1   # inner-loop sweep voltage  (was Yokogawa instrument1)
CH_STEP  = 2   # outer-loop step voltage   (was Yokogawa instrument2)
CH_FIXED = 3   # fixed bias voltage        (was Yokogawa instrument3 etc.)

# ----- voltages (Volts) -----
V_SCAN_START  =  0.0
V_SCAN_END    = -1.0
V_STEP_START  =  0.0
V_STEP_END    = -1.5
V_STEP_DELTA  = -0.5     # increment between successive V_step values
V_FIXED_VALUE = -0.5     # held constant during the entire measurement

# ----- safe ramp parameters (used when bringing voltages UP to start
#       values and DOWN to zero at the end of the run) -----
RAMP_STEP   = 0.005      # V per step  (small = safer for the device)
RAMP_DELAY  = 0.05       # s dwell between steps

# ----- measurement scan parameters -----
SCAN_STEP   = 0.02       # V per scan point  (sets V_scan resolution)
SCAN_DELAY  = 0.2        # s dwell at each scan point before reading DMM

# ----- current preamplifier gain (A / V) -----
# Choose ONE of: 1e-6, 1e-7, 1e-8, 1e-9
CURRENT_GAIN = 1e-7

# ----- output -----
# Timestamp captured at import time -> filename reflects the start of the run.
# Format YYYYMMDDhhmm matches the lab convention (e.g. ..._202605061646.txt).
_TIMESTAMP  = datetime.datetime.now().strftime("%Y%m%d%H%M")
SAVE_FNAME  = f"MQDL_ivvg_{_TIMESTAMP}.txt"
PLOT_TITLE  = "I-V_scan at various V_step  (V_fixed = {:.3f} V)".format(V_FIXED_VALUE)


# =============================================================================
# 2. helpers
# =============================================================================

def get_voltage(mqdl, channel, retries=3, retry_delay=0.1):
    """Read the present output voltage of an MQDL channel (V), with retries.

    The MQDL occasionally returns a malformed reply (e.g. just 'E' from a
    truncated 'ERR:..') if it is queried too soon after a set.  We retry
    a few times and, if still failing, fall back to the v2 channel cache.
    """
    last_err = None
    for _ in range(retries):
        try:
            _, vals = mqdl.get_value(channel)
            return float(vals[0])
        except (ValueError, TypeError) as e:
            last_err = e
            time.sleep(retry_delay)
    # last-resort: trust the v2 cache if it is populated
    cached = getattr(mqdl, "_channel_cache", {}).get(channel)
    if cached is not None:
        print(f"  [warn] ch{channel} read-back failed; using cached {cached:+.6f} V")
        return float(cached)
    raise RuntimeError(f"ch{channel} read-back failed after {retries} retries: {last_err}")


def stepwise_ramp(mqdl, channel, target, step, delay, label=""):
    """Move MQDL `channel` from its present voltage to `target` in safe
    increments of size `step` (V), waiting `delay` s between each set.

    Track progress by the COMMANDED value, not by reading back after every
    set — the MQDL firmware can return malformed replies if it is queried
    while still processing a recent set.  v2's cache makes the read-back
    redundant anyway.
    """
    present = get_voltage(mqdl, channel)         # one robust read at the start
    sgn_step = abs(step) if present < target else -abs(step)
    while abs(present - target) > abs(sgn_step) / 2:
        new_v = present + sgn_step
        # clamp on the last step so we land exactly on target
        if (sgn_step > 0 and new_v > target) or (sgn_step < 0 and new_v < target):
            new_v = target
        mqdl.set(channel, new_v)
        time.sleep(delay)
        present = new_v                          # trust the command
        print(f"  [ramp{label}] ch{channel} -> {present:+.6f} V")
    mqdl.set(channel, target)
    time.sleep(delay)
    print(f"  [ramp{label}] ch{channel} settled at {target:+.6f} V")


def read_dmm_volts(dmm):
    """Return the DMM reading in volts (preamp output)."""
    raw = dmm.query("fetch?")
    # Keithley 2000 returns something like '+1.234567E-03VDC,...'
    m = re.search(r'([+-]?\d+\.\d+E[+-]\d+)', raw)
    return float(m.group(1)) if m else float(raw)


def volts_to_nA(v_dmm, gain):
    """preamp: I_in [A] = V_out [V] * gain [A/V]   ->   nA"""
    return v_dmm * gain * 1e9


# =============================================================================
# 3. inner-loop sweep:  V_scan  ramped from start to end, DMM read at every point
# =============================================================================

def sweep_scan(mqdl, dmm, ch_scan, v_start, v_end, step, delay, gain):
    """Sweep V_scan from v_start to v_end in `step`-sized increments.
    Returns parallel lists of (V_scan, V_dmm, I_nA).

    V_scan is recorded as the COMMANDED voltage (no read-back) for the
    same reason as in stepwise_ramp.  After each set we wait `delay`
    seconds, then read the DMM (different instrument, no contention).
    """
    v_list, vdmm_list, i_list = [], [], []
    present = get_voltage(mqdl, ch_scan)         # one robust read at the start
    sgn_step = abs(step) if present < v_end else -abs(step)

    while abs(present - v_end) > abs(sgn_step) / 2:
        new_v = present + sgn_step
        if (sgn_step > 0 and new_v > v_end) or (sgn_step < 0 and new_v < v_end):
            new_v = v_end
        mqdl.set(ch_scan, new_v)
        time.sleep(delay)
        present = new_v                          # trust the command

        v_dmm = read_dmm_volts(dmm)
        i_nA  = volts_to_nA(v_dmm, gain)
        v_list.append(present)
        vdmm_list.append(v_dmm)
        i_list.append(i_nA)
        print(f"    V_scan = {present:+.6f} V    V_dmm = {v_dmm:+.6e} V"
              f"    I = {i_nA:+.4f} nA")

    return v_list, vdmm_list, i_list


# =============================================================================
# 4. main
# =============================================================================

def main():
    # ---- sanity checks ----
    assert len({CH_SCAN, CH_STEP, CH_FIXED}) == 3, \
        "CH_SCAN / CH_STEP / CH_FIXED must be three distinct channels"
    for ch in (CH_SCAN, CH_STEP, CH_FIXED):
        assert 1 <= ch <= 6, f"MQDL channel {ch} out of range 1..6"
    assert CURRENT_GAIN in (1e-6, 1e-7, 1e-8, 1e-9), \
        "CURRENT_GAIN must be one of 1e-6, 1e-7, 1e-8, 1e-9 A/V"

    # ---- open instruments ----
    mqdl = MQDL(MQDL_COM_PORT)
    rm   = pyvisa.ResourceManager()
    dmm  = rm.open_resource(DMM_ADDRESS)

    print("=== bringing all three channels UP to their start voltages ===")
    stepwise_ramp(mqdl, CH_FIXED, V_FIXED_VALUE, RAMP_STEP, RAMP_DELAY, " Vfix")
    stepwise_ramp(mqdl, CH_STEP,  V_STEP_START,  RAMP_STEP, RAMP_DELAY, " Vstep")
    stepwise_ramp(mqdl, CH_SCAN,  V_SCAN_START,  RAMP_STEP, RAMP_DELAY, " Vscan")

    # ---- generate the V_step list (inclusive of endpoints, like np.arange) ----
    v_step_values = np.arange(V_STEP_START, V_STEP_END, V_STEP_DELTA)
    print(f"V_step values: {v_step_values}")

    all_results = []   # list of (V_step, [V_scan], [V_dmm], [I_nA])

    try:
        for v_step in v_step_values:
            print(f"\n--- setting V_step = {v_step:+.6f} V (stepwise) ---")
            stepwise_ramp(mqdl, CH_STEP, float(v_step),
                          RAMP_STEP, RAMP_DELAY, " Vstep")

            print(f"--- returning V_scan to start = {V_SCAN_START:+.6f} V ---")
            stepwise_ramp(mqdl, CH_SCAN, V_SCAN_START,
                          RAMP_STEP, RAMP_DELAY, " Vscan")

            print(f"--- sweeping V_scan {V_SCAN_START:+.4f} -> {V_SCAN_END:+.4f} V ---")
            vs, vdmms, ins = sweep_scan(mqdl, dmm, CH_SCAN,
                                        V_SCAN_START, V_SCAN_END,
                                        SCAN_STEP, SCAN_DELAY, CURRENT_GAIN)
            all_results.append((float(v_step), vs, vdmms, ins))

    finally:
        # ---- always bring everything safely back to 0 V ----
        print("\n=== ramping all channels DOWN to 0 V ===")
        for ch, name in ((CH_SCAN, "Vscan"), (CH_STEP, "Vstep"), (CH_FIXED, "Vfix")):
            stepwise_ramp(mqdl, ch, 0.0, RAMP_STEP, RAMP_DELAY, f" {name}->0")

    # ---- save ----
    # columns: V_step  V_scan  V_dmm  I_nA   gain={CURRENT_GAIN}
    with open(SAVE_FNAME, "w") as f:
        f.write(f"# V_fixed = {V_FIXED_VALUE:.6f} V on ch{CH_FIXED}\n")
        f.write(f"# preamp gain = {CURRENT_GAIN:.0e} A/V\n")
        f.write("# V_step[V]  V_scan[V]  V_dmm[V]  I[nA]\n")
        for v_step, vs, vdmms, ins in all_results:
            for v, vd, ina in zip(vs, vdmms, ins):
                f.write(f"{v_step:+.6f} {v:+.6f} {vd:+.6e} {ina:+.6f}\n")
    print(f"\nSaved data -> {SAVE_FNAME}")

    # ---- plot ----
    plt.figure(figsize=(10, 6))
    for v_step, vs, _, ins in all_results:
        plt.plot(vs, ins, "-o", label=f"V_step = {v_step:+.3f} V")
    plt.xlabel("V_scan (V)")
    plt.ylabel("I (nA)")
    plt.title(PLOT_TITLE)
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
