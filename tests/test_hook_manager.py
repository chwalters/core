import unittest
import os
import mock as mock
import inspect
import shutil

from intelora.core.Models import Singleton

from intelora.core.ConfigurationManager import SettingLoader

from intelora.core import HookManager
from intelora.core.Models.Settings import Settings


class TestInit(unittest.TestCase):

    def setUp(self):
        # Init the folders, otherwise it raises an exceptions
        os.makedirs("/tmp/intelora/tests/intelora_resources_dir/neurons")
        os.makedirs("/tmp/intelora/tests/intelora_resources_dir/stt")
        os.makedirs("/tmp/intelora/tests/intelora_resources_dir/tts")
        os.makedirs("/tmp/intelora/tests/intelora_resources_dir/trigger")

        # get current script directory path. We are in /an/unknown/path/intelora/core/tests
        cur_script_directory = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
        # get parent dir. Now we are in /an/unknown/path/intelora
        root_dir = os.path.normpath(cur_script_directory + os.sep + os.pardir)

        self.settings_file_to_test = root_dir + os.sep + "tests/settings/settings_test.yml"
        self.settings = SettingLoader(file_path=self.settings_file_to_test)

    def tearDown(self):
        # Cleanup
        shutil.rmtree('/tmp/intelora/tests/intelora_resources_dir')

        Singleton._instances = {}

    def test_on_start(self):
        """
        test list of synapse
        """
        with mock.patch("intelora.core.SynapseLauncher.start_synapse_by_list_name") as mock_synapse_launcher:
            HookManager.on_start()
            mock_synapse_launcher.assert_called_with(["on-start-synapse", "bring-led-on"], new_lifo=True)
            mock_synapse_launcher.reset_mock()

    def test_on_waiting_for_trigger(self):
        """
        test with single synapse 
        """
        with mock.patch("intelora.core.SynapseLauncher.start_synapse_by_name") as mock_synapse_launcher:
            HookManager.on_waiting_for_trigger()
            mock_synapse_launcher.assert_called_with("test", new_lifo=True)
            mock_synapse_launcher.reset_mock()

    def test_on_triggered(self):
        with mock.patch("intelora.core.SynapseLauncher.start_synapse_by_list_name") as mock_synapse_launcher:
            HookManager.on_triggered()
            mock_synapse_launcher.assert_called_with(["on-triggered-synapse"], new_lifo=True)
            mock_synapse_launcher.reset_mock()

    def test_on_start_listening(self):
        self.assertIsNone(HookManager.on_start_listening())

    def test_on_stop_listening(self):
        self.assertIsNone(HookManager.on_stop_listening())

    def test_on_order_found(self):
        self.assertIsNone(HookManager.on_order_found())

    def test_on_order_not_found(self):
        with mock.patch("intelora.core.SynapseLauncher.start_synapse_by_list_name") as mock_synapse_launcher:
            HookManager.on_order_not_found()
            mock_synapse_launcher.assert_called_with(["order-not-found-synapse"], new_lifo=True)
            mock_synapse_launcher.reset_mock()

    def test_on_mute(self):
        """
        test that empty list of synapse return none
        """
        self.assertIsNone(HookManager.on_mute())


if __name__ == '__main__':
    unittest.main()

    # suite = unittest.TestSuite()
    # suite.addTest(TestInit("test_main"))
    # runner = unittest.TextTestRunner()
    # runner.run(suite)
