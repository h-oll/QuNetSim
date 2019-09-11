from queue import Queue
from components import protocols
from components.logger import Logger
from components.daemon_thread import DaemonThread
import uuid


class Host:
    """ Host object acting as either a router node or an application host node. """

    def __init__(self, host_id, cqc, role='host'):
        """
        Return the most important thing about a person.

        Args:
            host_id: The ID of the host
            cqc: The CQC for this host

        """
        self.host_id = host_id
        self._packet_queue = Queue()
        self._stop_thread = False
        self._data_qubit_store = {}
        self._classical = []
        self._EPR_store = {}
        self._queue_processor_thread = None
        self.connections = []
        self.cqc = cqc
        self.logger = Logger.get_instance()
        self.role = role
        self.seq_number = {}

    def rec_packet(self, packet):
        """
        Return the most important thing about a person.

        Args:
            packet: A string indicating the name of the person.

        """
        self._packet_queue.put(packet)

    def add_connection(self, receiver_id):
        """
        Adds the connection to host with ID *connection_id*.

        Args:
            receiver_id (string): The ID of the host to connect with.

        """
        self.connections.append(receiver_id)

    def _get_sequence_number(self, receiver):
        if receiver not in self.seq_number:
            self.seq_number[receiver] = 0
        else:
            self.seq_number[receiver] += 1
        return self.seq_number[receiver]

    def send_classical(self, receiver, message):
        """
        Sends the classical message *message*  to the receiver host with
        id *receiver*

        Args:
            receiver (string): The ID of the host to send the message.
            message (string): The classical message to send.

        """
        packet = protocols.encode(self.host_id, receiver, protocols.SEND_CLASSICAL, message, protocols.CLASSICAL,
                                  self._get_sequence_number(receiver))
        self.logger.log('sent classical')
        self._packet_queue.put(packet)

    def send_epr(self, receiver_id):
        """
        Establish an EPR pair with the receiver and return the qubit
        ID of pair.

        Args:
            receiver_id (string): The receiver ID


        Returns:
            string: The qubit ID of the EPR pair.

        """
        q_id = str(uuid.uuid4())
        packet = protocols.encode(sender=self.host_id,
                                  receiver=receiver_id,
                                  protocol=protocols.SEND_EPR,
                                  payload=q_id,
                                  payload_type=protocols.SIGNAL,
                                  sequence_num=self._get_sequence_number(receiver_id))
        self.logger.log(self.host_id + " sends EPR to " + receiver_id)
        self._packet_queue.put(packet)
        return q_id

    def send_teleport(self, receiver, q):
        """
        Teleport the qubit *q* with the receiver with host ID *receiver*

        Args:
            receiver (string): The ID of the host to establish the EPR pair with.
            q (Qubit): The qubit to teleport.

        """
        self.seq_number[receiver] = 0
        packet = protocols.encode(self.host_id, receiver, protocols.SEND_TELEPORT, {'q': q}, protocols.SIGNAL,
                                  self._get_sequence_number(receiver))

        self.logger.log(self.host_id + " sends TELEPORT to " + receiver)
        self._packet_queue.put(packet)

    def send_superdense(self, receiver_id, message):
        """
        Send the two bit binary (i.e. '00', '01', '10', '11) message via superdesne
        coding to the receiver with receiver ID *receiver_id*.

        Args:
            receiver_id (string): The receiver ID to send the message to
            message (string): The two bit binary message

        """
        packet = protocols.encode(self.host_id, receiver_id, protocols.SEND_SUPERDENSE, message, protocols.CLASSICAL,
                                  self._get_sequence_number(receiver_id))
        self.logger.log(self.host_id + " sends SUPERDENSE to " + receiver_id)
        self._packet_queue.put(packet)

    def shares_epr(self, receiver_id):
        """
        Returns boolean value dependant on if the host shares an EPR pair
        with receiver with ID *receiver_id*

        Args:
            receiver_id (string): The receiver ID to check.

        Returns:
             boolean: whether the host shares an EPR pair with receiver with ID *receiver_id*
        """
        return receiver_id in self._EPR_store and len(self._EPR_store[receiver_id]) != 0

    def _process_message(self, message):
        sender = message['sender']

        if sender not in self._data_qubit_store and sender != self.host_id:
            self._data_qubit_store[sender] = []

        if sender not in self._EPR_store and sender != self.host_id:
            self._EPR_store[sender] = []

        result = protocols.process(message)
        if result is not None:
            if 'sequence_number' not in result.keys():
                self._classical.append({'sender': sender, 'message': result['message']})
                self.logger.log(self.cqc.name + ' received ' + result['message'])
            else:
                self._classical.append(
                    {'sender': sender, 'message': result['message'], 'sequence_number': result['sequence_number']})
                self.logger.log(self.cqc.name + ' received ' + result['message'] + ' with sequence number ' + str(
                    result['sequence_number']))

    def _process_queue(self):
        self.logger.log('Host ' + self.host_id + ' started processing')
        while True:
            if self._stop_thread:
                break

            if not self._packet_queue.empty():
                message = self._packet_queue.get()
                if not message:
                    raise Exception('empty message')
                DaemonThread(self._process_message, args=(message,))

    def add_epr(self, partner_id, qubit, q_id=None):
        if partner_id not in self._EPR_store and partner_id != self.host_id:
            self._EPR_store[partner_id] = []

        if q_id is None:
            q_id = str(uuid.uuid4())

        to_add = {'q': qubit, 'q_id': q_id, 'blocked': False}

        self._EPR_store[partner_id].append(to_add)
        self.logger.log(self.host_id + ' added EPR pair ' + q_id + ' with partner ' + partner_id)
        return q_id

    def add_data_qubit(self, partner_id, qubit, q_id=None):
        if partner_id not in self._data_qubit_store and partner_id != self.host_id:
            self._data_qubit_store[partner_id] = []

        if q_id is None:
            q_id = str(uuid.uuid4())

        to_add = {'q': qubit, 'q_id': q_id, 'blocked': False}

        self._data_qubit_store[partner_id].append(to_add)
        self.logger.log(self.host_id + ' added data qubit ' + q_id + ' from ' + partner_id)
        return q_id

    def get_epr(self, partner_id, q_id=None):
        if partner_id not in self._EPR_store:
            return None

        if len(self._EPR_store[partner_id]) == 0:
            return None

        # If q_id is not specified, then return the last in the stack
        # else return the qubit with q_id q_id
        if q_id is None:
            if partner_id not in self._EPR_store or len(self._EPR_store[partner_id]) == 0:
                return None
            if not self._EPR_store[partner_id][-1]['blocked']:
                self._EPR_store[partner_id][-1]['blocked'] = True
                return self._EPR_store[partner_id].pop()
            else:
                self.logger.log('accessed blocked epr qubit')
        else:
            for index, qubit in enumerate(self._EPR_store[partner_id]):
                if qubit['q_id'] == q_id:
                    q = qubit['q']
                    del self._EPR_store[partner_id][index]
                    return q
        return None

    def get_data_qubit(self, partner_id, q_id=None):
        if partner_id not in self._data_qubit_store:
            return None

        # If q_id is not specified, then return the last in the stack
        # else return the qubit with q_id q_id
        if q_id is None:
            if partner_id not in self._data_qubit_store or len(self._data_qubit_store[partner_id]) == 0:
                return None
            if not self._data_qubit_store[partner_id][-1]['blocked']:
                self._data_qubit_store[partner_id][-1]['blocked'] = True
                return self._data_qubit_store[partner_id].pop()
            else:
                print('accessed blocked data qubit')
        else:
            for index, qubit in enumerate(self._data_qubit_store[partner_id]):
                if qubit['q_id'] == q_id:
                    q = qubit['q']
                    del self._data_qubit_store[partner_id][index]
                    return q
        return None

    def get_classical_messages(self):
        return sorted(self._classical, key=lambda x: x['sequence_number'])

    def stop(self):
        self.logger.log('Host ' + self.host_id + " stopped")
        self._stop_thread = True

    def start(self):
        self._queue_processor_thread = DaemonThread(target=self._process_queue)