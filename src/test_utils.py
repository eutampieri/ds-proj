from twisted.internet import reactor
from twisted.internet.defer import Deferred
from twisted.internet.protocol import Factory
from test.mocks import MockLDAPClient, MockLDAPServer

class TestEnvironment:
    """Utility module for testing multiple servers and clients together."""

    def __init__(self):
        self.__actions = Deferred()
        self.__clients = []
        self.__servers = []
        self.__succeeded = True
        self.__stopped = False

    def tearDown(self):
        [port.stopListening() for port in self.__servers]

    def addServer(self, port: int, server: type[MockLDAPServer]) -> None:
        """Adds a server to the reactor."""
        serverName = server.__name__

        def _createServer(res):
            factory = Factory()
            factory.protocol = server
            self.__servers.append(reactor.listenTCP(port, factory))
            print(f"[{serverName}] Running on port {port}...")

        self.__actions.addCallback(lambda _: print(f"[{serverName}] Starting..."))
        return self.__actions.addCallback(_createServer)

    def addClient(self, port: int, client: MockLDAPClient) -> Deferred:
        """Adds a client to the reactor. Returns the Deferred of the client"""
        clientName = client.__class__.__name__

        def _createClient(res, clientIndex):
            d = client.run(f"tcp:localhost:{port}")
            d.addCallback(lambda _: print(f"[{clientName}] Client requesting to port {port}"))
            d.chainDeferred(self.__clients[clientIndex])
            return d

        # empty deferred, for accumulating callbacks
        self.__clients.append(Deferred())
        index = len(self.__clients) - 1

        self.__actions.addCallback(lambda _: print(f"[{clientName}] Starting..."))
        self.__actions.addCallback(_createClient, index)
        return self.__clients[index]

    def addTimeout(self, seconds: float) -> None:
        """Adds a timeout (in seconds) for execution"""
        self.__actions.addTimeout(seconds, reactor, lambda err, f: self.fail('Timeout elapsed.'))

    def then(self, callback) -> None:
        """Executes a callback after all the previous ones are completed"""
        self.__actions.addCallback(callback)
    
    def catch(self, errback) -> None:
        """Catches an error, and executes the errback function"""
        self.__actions.addErrback(errback)

    def run(self) -> bool:
        """Starts the test. Returns true if ran successfully, false if it failed."""
        self.catch(self.fail)
        reactor.callLater(0, self.__actions.callback, None)
        try:
            reactor.run()
            return self.__succeeded
        except Exception:
            return False

    def __stop(self, ignored=None) -> None:
        """Stops the test."""
        if not self.__stopped:
            self.__stopped = True
            reactor.stop()

    def succeed(self, ignored=None) -> None:
        """Ends the test as succeeded."""
        if not self.__stopped:
            self.__succeeded = True
            print(f"-- TEST PASSED --")
            self.__stop()

    def fail(self, error: str='') -> None:
        """Ends the test as failed."""
        if not self.__stopped:
            self.__succeeded = False
            print(f"-- TEST FAILED -- {error}")
            self.__stop()


if __name__ == "__main__":
    ### Testing the testing environment ###
    from test.mocks import AcceptBind, RejectBind, UnresponsiveBind, BindingClient

    # create the test environment
    test = TestEnvironment()

    # add some servers to the test
    test.addServer(port=3890, server=AcceptBind)
    test.addServer(port=3891, server=RejectBind)
    test.addServer(port=3892, server=UnresponsiveBind)

    # add a client, and define some callbacks over it
    clientDeferred = test.addClient(port=3892, client=BindingClient('cn=admin,dc=example,dc=org', 'password'))

    clientDeferred.addCallback(test.fail)
    clientDeferred.addErrback(test.succeed)
    
    # set a timeout for the execution
    test.addTimeout(seconds=5)

    # execute the test
    assert test.run()