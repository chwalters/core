#!/usr/bin/env python
# coding: utf8
import argparse
import logging

import time

from random import *
from intelora.core import ShellGui
from intelora.core import Utils
from intelora.core.ConfigurationManager import SettingLoader
from intelora.core.ConfigurationManager.BrainLoader import BrainLoader
from intelora.core.SignalLauncher import SignalLauncher
from intelora.core.Utils.RpiUtils import RpiUtils
from flask import Flask
from intelora.core.RestAPI.FlaskAPI import FlaskAPI

from ._version import version_str
import signal
import sys

from intelora.core.ResourcesManager import ResourcesManager
from intelora.core.SynapseLauncher import SynapseLauncher
from intelora.core.OrderAnalyser import OrderAnalyser

logging.basicConfig()
logger = logging.getLogger("intelora")


def signal_handler(signal, frame):
    """
    Press Ctrl+C to terminate Intelora

    :param signal: signal handler
    :param frame: execution frame

    """
    print("\n")
    Utils.print_info("Intelora stopped")
    sys.exit(0)

# actions available
ACTION_LIST = ["start", "gui", "install", "uninstall"]


def parse_args(args):
    """
    Parsing function
    :param args: arguments passed from the command line
    :return: return parser
    """
    # create arguments
    parser = argparse.ArgumentParser(description='Intelora')
    parser.add_argument("action", help="[start|gui|install|uninstall]")
    parser.add_argument("--run-synapse",
                        help="Name of a synapse to load surrounded by quote")
    parser.add_argument("--run-order", help="order surrounded by a quote")
    parser.add_argument("--brain-file", help="Full path of a brain file")
    parser.add_argument("--debug", action='store_true',
                        help="Show debug output")
    parser.add_argument("--git-url", help="Git URL of the neuron to install")
    parser.add_argument("--neuron-name", help="Neuron name to uninstall")
    parser.add_argument("--stt-name", help="STT name to uninstall")
    parser.add_argument("--tts-name", help="TTS name to uninstall")
    parser.add_argument("--trigger-name", help="Trigger name to uninstall")
    parser.add_argument("--signal-name", help="Signal name to uninstall")
    parser.add_argument('-v', '--version', action='version',
                        version='Intelora ' + version_str)

    # parse arguments from script parameters
    return parser.parse_args(args)


def main():
    """Entry point of Intelora program."""
    # parse argument. the script name is removed
    try:
        parser = parse_args(sys.argv[1:])
    except SystemExit:
        sys.exit(1)

    # check if we want debug
    configure_logging(debug=parser.debug)

    logger.debug("intelora args: %s" % parser)

    # by default, no brain file is set.
    # Use the default one: brain.yml in the root path
    brain_file = None

    # check if user set a brain.yml file
    if parser.brain_file:
        brain_file = parser.brain_file

    # check the user provide a valid action
    if parser.action not in ACTION_LIST:
        Utils.print_warning("%s is not a recognised action\n" % parser.action)
        sys.exit(1)

    # install modules
    if parser.action == "install":
        if not parser.git_url:
            Utils.print_danger("You must specify the git url")
            sys.exit(1)
        else:
            parameters = {
                "git_url": parser.git_url
            }
            res_manager = ResourcesManager(**parameters)
            res_manager.install()
        return

    # uninstall modules
    if parser.action == "uninstall":
        if not parser.neuron_name \
                and not parser.stt_name \
                and not parser.tts_name \
                and not parser.trigger_name\
                and not parser.signal_name:
            Utils.print_danger("You must specify a module name with "
                               "--neuron-name "
                               "or --stt-name "
                               "or --tts-name "
                               "or --trigger-name "
                               "or --signal-name")
            sys.exit(1)
        else:
            res_manager = ResourcesManager()
            res_manager.uninstall(neuron_name=parser.neuron_name,
                                  stt_name=parser.stt_name,
                                  tts_name=parser.tts_name,
                                  trigger_name=parser.trigger_name,
                                  signal_name=parser.signal_name)
        return

    # load the brain once
    brain_loader = BrainLoader(file_path=brain_file)
    brain = brain_loader.brain

    # load settings
    # get global configuration once
    settings_loader = SettingLoader()
    settings = settings_loader.settings

    if parser.action == "start":

        # user set a synapse to start
        if parser.run_synapse is not None:
            SynapseLauncher.start_synapse_by_name(parser.run_synapse,
                                                  brain=brain)

        if parser.run_order is not None:
            SynapseLauncher.run_matching_synapse_from_order(parser.run_order,
                                                            brain=brain,
                                                            settings=settings,
                                                            is_api_call=False)

        if (parser.run_synapse is None) and (parser.run_order is None):
            # start rest api
            start_rest_api(settings, brain)
            start_intelora(settings, brain)

    if parser.action == "gui":
        try:
            ShellGui(brain=brain)
        except (KeyboardInterrupt, SystemExit):
            Utils.print_info("Intelora stopped")
            sys.exit(0)


class AppFilter(logging.Filter):
    """
    Class used to add a custom entry into the logger
    """
    def filter(self, record):
        record.app_version = "intelora-%s" % version_str
        return True


def configure_logging(debug=None):
    """
    Prepare log folder in current home directory.

    :param debug: If true, set the lof level to debug

    """
    logger = logging.getLogger("intelora")
    logger.addFilter(AppFilter())
    logger.propagate = False
    syslog = logging.StreamHandler()
    syslog .setLevel(logging.DEBUG)

    formatter = logging.Formatter('%(asctime)s :: %(app_version)s :: %(message)s', "%Y-%m-%d %H:%M:%S")
    syslog .setFormatter(formatter)

    if debug:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    # add the handlers to logger
    logger.addHandler(syslog)

    logger.debug("Logger ready")


def get_list_signal_class_to_load(brain):
    """
    Return a list of signal class name
    For all synapse, each signal type is added to a list only if the signal is not yet present in the list
    :param brain: Brain object
    :type brain: Brain
    :return: set of signal class
    """
    list_signal_class_name = set()

    for synapse in brain.synapses:
        for signal_object in synapse.signals:
            list_signal_class_name.add(signal_object.name)
    logger.debug("[Kalliope entrypoint] List of signal class to load: %s" % list_signal_class_name)
    return list_signal_class_name


def start_rest_api(settings, brain):
    """
    Start the Rest API if asked in the user settings
    """
    # run the api if the user want it
    if settings.rest_api.active:
        Utils.print_info("Starting REST API Listening port: %s" % settings.rest_api.port)
        app = Flask(__name__)
        flask_api = FlaskAPI(app=app,
                             port=settings.rest_api.port,
                             brain=brain,
                             allowed_cors_origin=settings.rest_api.allowed_cors_origin)
        flask_api.daemon = True
        flask_api.start()


def start_intelora(settings, brain):
    """
    Start all signals declared in the brain
    """
    # start intelora
    Utils.print_success("")
    Utils.print_success("Intelora is initializing the agent:")
    time.sleep(randint(1, 3))
    Utils.print_success("Brain................[OK]")
    time.sleep(randint(1, 3))
    Utils.print_success("Neurons..............[OK]")
    time.sleep(randint(1, 3))
    Utils.print_success("Synapses.............[OK]")
    time.sleep(randint(1, 3))
    Utils.print_success("Speech Recognizer....[OK]")
    time.sleep(randint(1, 3))
    Utils.print_success("Order Manager........[OK]")
    time.sleep(randint(1, 3))
    Utils.print_success("Speech Synthesizer...[OK]")
    time.sleep(randint(1, 3))
    Utils.print_success("Triggers.............[OK]")
    time.sleep(randint(1, 3))
    Utils.print_success("Variables............[OK]")
    time.sleep(randint(1, 3))
    Utils.print_success("")
    Utils.print_success("Agent is now online!")
    Utils.print_success("")
    Utils.print_info("Press Ctrl+C to stop Intelora")
    # catch signal for killing on Ctrl+C pressed
    signal.signal(signal.SIGINT, signal_handler)

    # get a list of signal class to load from declared synapse in the brain
    # this list will contain string of signal class type.
    # For example, if the brain contains multiple time the signal type "order", the list will be ["order"]
    # If the brain contains some synapse with "order" and "event", the list will be ["order", "event"]
    list_signals_class_to_load = get_list_signal_class_to_load(brain)

    # start each class name
    try:
        for signal_class_name in list_signals_class_to_load:
            signal_instance = SignalLauncher.launch_signal_class_by_name(signal_name=signal_class_name,
                                                                         settings=settings)
            if signal_instance is not None:
                signal_instance.daemon = True
                signal_instance.start()

        while True:  # keep main thread alive
            time.sleep(0.1)

    except (KeyboardInterrupt, SystemExit):
        # we need to switch GPIO pin to default status if we are using a Rpi
        if settings.rpi_settings:
            Utils.print_info("GPIO cleaned")
            logger.debug("Clean GPIO")
            import RPi.GPIO as GPIO
            GPIO.cleanup()
