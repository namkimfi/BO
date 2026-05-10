import pyvisa as visa
import matplotlib.pyplot as plt
import time
import numpy as np

import signal
import contextlib

from SOURCE import SOURCE

class KeyboardInterruptContext:
    def __enter__(self):
        # Set up a signal handler for SIGINT (keyboard interrupt)
        self.original_handler = signal.signal(signal.SIGINT, signal.SIG_IGN)

    def __exit__(self, exc_type, exc_value, traceback):
        # Restore the original signal handler for SIGINT
        signal.signal(signal.SIGINT, self.original_handler)

class MQDL(SOURCE):
    """
    Represents a MQDL Voltage source.
    Inherits from the SOURCE class.
    
    Attributes:
    - num_channel (int): Number of channels (6 in this case).
    """
    num_channel = 6

    def __init__(self, address):
        super().__init__(address, 'ASRL')

        self._channel_cache = {ch: None for ch in range(1, self.num_channel + 1)}

        for ch in range(1, self.num_channel + 1):
            try:
                _, vals = self.get_value(ch)
                self._channel_cache[ch] = vals[0]
            except:
                self._channel_cache[ch] = None

    def get_value(self, *args):
        """
        Initialize an MQDL instrument object.
        
        Parameters:
        - address (str): The address of the instrument in ASRL format.
        """
        values = []
        for arg in args:
            try:
                values.append(float(self.inst.query("?{}".format(arg)).split('\r')[0]))
            except ValueError:
                values.append(float(self.inst.query("?{}".format(arg)).split('\r')[0].replace('!', '-1')))
            except:
                return "Error Occured.", "Error Occured."
        return str(args), values

    def set(self, channel, To):
        """
        Get values from the MQDL instrument.
        
        Parameters:
        - *args: Variable arguments representing the channels to query.
        
        Returns:
        - tuple: A tuple containing the queried channels and their corresponding values.
        """
        if self._channel_cache[channel] == To:
            return

        with KeyboardInterruptContext():
            self.inst.write('S{}:{:.7f}'.format(channel, To))
        self._channel_cache[channel] = To

    def ramp(self, channel, To):
        if self._channel_cache[channel] == To:
            return

        with KeyboardInterruptContext():
            self.inst.write('R{}:{:.7f}:50\n'.format(channel, To))
        self._channel_cache[channel] = To

    def manyset(self, *args):
        with KeyboardInterruptContext():
            for arg in args:
                self.set(arg[0], arg[1])

    def manyramp(self, *args):
        with KeyboardInterruptContext():
            for arg in args:
                self.ramp(arg[0], arg[1])

    def zero(self):
        with KeyboardInterruptContext():
            for i in range(1, 7):
                self.inst.write('Z{}:50'.format(i))
            for i in range(1, 7):
                self._channel_cache[i] = 0.0