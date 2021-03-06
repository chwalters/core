import sys

from intelora.core.NeuronModule import NeuronModule


class Kill_switch(NeuronModule):
    """
    Class used to exit Intelora process from system command
    """
    def __init__(self, **kwargs):
        super(Kill_switch, self).__init__(**kwargs)
        sys.exit()
