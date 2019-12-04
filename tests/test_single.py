import unittest
import time
import sys
import os

from cqc.pythonLib import CQCConnection, qubit
from simulaqron.network import Network as SimulaNetwork
from simulaqron.settings import simulaqron_settings

sys.path.append("../..")
from components.host import Host
from components.network import Network


@unittest.skip('')
class TestTwoHop(unittest.TestCase):
    sim_network = None
    network = None
    hosts = None
    MAX_WAIT = 20

    @classmethod
    def setUpClass(cls):
        simulaqron_settings.default_settings()
        nodes = ['Alice', 'Bob', 'Eve']
        cls.sim_network = SimulaNetwork(nodes=nodes, force=True)
        cls.sim_network.start()

        cls.network = Network.get_instance()
        cls.network.start()

        # if os.path.exists('./components/__pycache__'):
        #     os.system('rm -rf ./components/__pycache__/')

    @classmethod
    def tearDownClass(cls):
        if cls.sim_network is not None:
            cls.sim_network.stop()
        simulaqron_settings.default_settings()

        cls.network.stop()
        cls.network = None

    def tearDown(self):
        for key in self.hosts.keys():
            self.hosts[key].cqc.flush()
            self.hosts[key].stop()
            self.network.remove_host(self.hosts[key])


    # @unittest.skip('')
    def test_superdense(self):
        with CQCConnection("Alice") as Alice, CQCConnection("Bob") as Bob, CQCConnection("Eve") as Eve:
            hosts = {'alice': Host('00000000', Alice),
                     'bob': Host('00000001', Bob),
                     'eve': Host('00000011', Eve)}
            self.hosts = hosts

            # A <-> B <-> E
            hosts['alice'].add_connection('00000001')
            hosts['bob'].add_connection('00000000')

            hosts['bob'].add_connection('00000011')
            hosts['eve'].add_connection('00000001')

            hosts['alice'].start()
            hosts['bob'].start()
            hosts['eve'].start()

            for h in hosts.values():
                self.network.add_host(h)

            hosts['alice'].send_superdense(hosts['bob'].host_id, '10')

            messages = hosts['bob'].classical
            i = 0
            while i < TestTwoHop.MAX_WAIT and len(messages) == 0:
                messages = hosts['bob'].classical
                i += 1
                time.sleep(1)

            self.assertTrue(len(messages) > 0)
            self.assertEqual(messages[0]['sender'], hosts['alice'].host_id)
            self.assertEqual(messages[0]['message'], '10')
