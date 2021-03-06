from components.host import Host
from components.network import Network
from components.logger import Logger

Logger.DISABLED = True


def protocol_1(host, receiver):
    # Here we write the protocol code for a host.
    for i in range(5):
        print('Sending EPR pair %d' % (i + 1))
        epr_id, ack_arrived = host.send_epr(receiver, await_ack=True)

        if ack_arrived:
            # Receiver got the EPR pair and ACK came back
            # safe to use the EPR pair.
            q = host.get_epr(receiver, q_id=epr_id)
            print('Host 1 measured: %d' % q.measure())
        else:
            print('The EPR pair was not properly established')
    print('Sender protocol done')


def protocol_2(host, sender):
    """
    Receiver protocol for receiving 5 EPR pairs.

    Args:
        host (Host): The sender Host.
        sender (str): The ID of the sender of the EPR pairs.
    """

    # Host 2 waits 5 seconds for the EPR to arrive.
    for _ in range(5):
        q = host.get_epr(sender, wait=5)
        # q is None if the wait time expired.
        if q is not None:
            print('Host 2 measured: %d' % q.measure())
        else:
            print('Host 2 did not receive an EPR pair')
    print('Receiver protocol done')


def main():
    network = Network.get_instance()
    nodes = ['A', 'B', 'C']
    network.start(nodes)
    network.delay = 0.1

    host_A = Host('A')
    host_A.add_connection('B')
    host_A.start()

    host_B = Host('B')
    host_B.add_connection('A')
    host_B.add_connection('C')
    host_B.start()

    host_C = Host('C')
    host_C.add_connection('B')
    host_C.start()

    network.add_host(host_A)
    network.add_host(host_B)
    network.add_host(host_C)

    host_A.run_protocol(protocol_1, (host_C.host_id,))
    host_C.run_protocol(protocol_2, (host_A.host_id,))


if __name__ == '__main__':
    main()
