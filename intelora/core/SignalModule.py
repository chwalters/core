import logging
from intelora.core import Utils

from intelora.core.ConfigurationManager import BrainLoader

logging.basicConfig()
logger = logging.getLogger("intelora")


class MissingParameter(Exception):
    """
    An exception when parameters are missing from signals.

    """
    pass


class SignalModule(object):

    def __init__(self, **kwargs):
        super(SignalModule, self).__init__(**kwargs)
        # get the child who called the class
        self.signal_name = self.__class__.__name__

        Utils.print_info('Init Signal :' + self.signal_name)
        self.brain = BrainLoader().brain

    def get_list_synapse(self):
        for synapse in self.brain.synapses:
            for signal in synapse.signals:
                # if the signal is a child we add it to the synapses list
                if signal.name == self.signal_name.lower(): # Lowercase !
                    if not self.check_parameters(parameters=signal.parameters):
                        logger.debug(
                            "[SignalModule] The signal " + self.signal_name + " is missing mandatory parameters, check documentation")
                        raise MissingParameter()
                    else:
                        yield synapse
                        break # if there is multiple signals in the synapse, we only add it once !

    @staticmethod
    def check_parameters(parameters):
        raise NotImplementedError("[SignalModule] Must override check_parameters method !")