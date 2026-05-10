import pyvisa as visa
import matplotlib.pyplot as plt
import time
import numpy as np

import signal
import contextlib

class SOURCE:
    instances = []

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        # cls.instances = []

    def __init__(self, address, connection_type):
        if connection_type == 'MASTER':
            return 

        rm = visa.ResourceManager()
        if connection_type == 'ASRL':
            self.inst = rm.open_resource('ASRL{}::INSTR'.format(address))
            self.inst.baud_rate = 28800
            # Serial line terminations.  Determined empirically with
            # data/diagnose_mqdl_termination.py:
            #   * '?n' queries are answered ONLY when the request is
            #     terminated with '\r\n'; '' and '\r' are silently
            #     ignored, '\n' alone produces a duplicated response.
            #   * the device terminates responses with b'\r\n' (CRLF).
            # Using '\r\n' for writes also makes plain set/ramp commands
            # unambiguously delimited, which avoids stepwise_ramp losing
            # individual sets when commands arrive faster than the
            # documented 50 ms quiet period.
            self.inst.read_termination  = '\r\n'
            self.inst.write_termination = '\r\n'
            self.inst.timeout = 2000  # ms

        elif connection_type == 'GPIB':
            self.inst = rm.open_resource('GPIB0::{}::INSTR'.format(address))
        else:
            raise ValueError('Invalid connection type: {}'.format(connection_type))

        self.__class__.instances.append(self)

    def get_value(self, *args):
        pass
    
    def set(self, channel, To):
        pass
    
    def ramp(self, channel, To):
        pass
    
    def manyset(self, *args):
        pass
    
    def manyramp(self, *args):
        pass
    
    def zero(self):
        pass
    
    @classmethod
    def zero_all(cls):
        for instance in cls.instances:
            instance.zero()
