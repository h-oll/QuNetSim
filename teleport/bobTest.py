from cqc.pythonLib import CQCConnection
from functions import receive_teleport


#####################################################################################################
#
# main
#
def main():
    # Initialize the connection
    with CQCConnection("Bob") as Bob:
        qB = receive_teleport(Bob)
        m = qB.measure()
        print("Measurement outcome: ", m)


##################################################################################################
main()
