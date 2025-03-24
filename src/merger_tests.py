import unittest
import twisted.internet.error
from twisted.trial import unittest as twistedtest
from test.mocks import *
from test_utils import TestEnvironment
from proxy.merger import ProxyMerger
from twisted.internet.protocol import Factory
from ldaptor.protocols.ldap import ldaperrors

### Tests for the LDAP proxy merger ###

# 1. Bind: the client should bind if he's registered to the proxy
# 2. Search: the search should be done on all the server
# 3. Consistency over Availability
# 4. Read-only proxy: only queries should be allowed
# 5. Database error handling

class TestProxyMerger(twistedtest.TestCase):

    def startServer(self, port: int, server: type[MockLDAPServer]):
        """Start a server. Automagically cleanup the server on test end."""
        factory = Factory()
        factory.protocol = server
        listening_port = reactor.listenTCP(port, factory)
        self.addCleanup(listening_port.stopListening)
        return listening_port

    def startClient(self, port: int, client: MockLDAPClient) -> Deferred:
        """Start a client. Automagically cleanup the client on test end."""
        d = client.run("localhost", port)
        self.addCleanup(client.close)
        return d

    def tearDown(self):
        self.flushLoggedErrors(twisted.internet.error.ConnectionDone) # ignore the connection closed error
        for call in reactor.getDelayedCalls():
            if call.active():
                call.cancel()

    def succeed(self, ignored=None):
        """Shorthand for succeeding a test."""
        self.successResultOf(defer.succeed(True))

    def fail(self, ignored=None):
        super().fail()

    ### TESTS ###

    def test_registered_client_should_bind(self):
        # config
        client = ClientEntry('cn=client,dc=example,dc=org', 'clientpassword')
        servers = [
            ServerEntry('127.0.0.1', 3890, 'dc=example,dc=org', 'cn=proxy,dc=example,dc=org', 'proxypassword'),
            ServerEntry('127.0.0.1', 3891, 'dc=example,dc=org', 'cn=proxy,dc=example,dc=org', 'proxypassword'),
        ]

        # start server
        for s in servers:
            self.startServer(port=s.port, server=AcceptBind)

        # start proxy
        proxy = lambda: ProxyMerger(OneClientDatabase(client, servers))
        self.startServer(port=10389, server=proxy)

        # start client
        clientDef = self.startClient(port=10389, client=BindingClient(client.dn, client.password))
        clientDef.addCallback(self.succeed)
        clientDef.addErrback(self.fail)

        # wait completion
        return clientDef

    def test_unregistered_client_should_not_bind(self):
        # config
        client = ClientEntry('cn=client,dc=example,dc=org', 'clientpassword')
        servers = [
            ServerEntry('127.0.0.1', 3890, 'dc=example,dc=org', 'cn=proxy,dc=example,dc=org', 'proxypassword'),
            ServerEntry('127.0.0.1', 3891, 'dc=example,dc=org', 'cn=proxy,dc=example,dc=org', 'proxypassword'),
        ]

        # start server
        for s in servers:
            self.startServer(port=s.port, server=AcceptBind)

        # start proxy
        proxy = lambda: ProxyMerger(OneClientDatabase(client, servers))
        self.startServer(port=10389, server=proxy)

        # start client
        clientDef = self.startClient(port=10389, client=BindingClient('cn=worng,dc=example,dc=org', 'wrongpassword'))
        clientDef.addCallback(self.fail)
        clientDef.addErrback(self.succeed)
        clientDef.addTimeout(5, reactor, onTimeoutCancel=lambda err, t: self.fail())

        # wait completion
        return clientDef

    def test_bind_should_fail_when_one_server_is_unavailable(self):
        # config
        client = ClientEntry('cn=client,dc=example,dc=org', 'clientpassword')
        servers = [
            ServerEntry('127.0.0.1', 3890, 'dc=example,dc=org', 'cn=proxy,dc=example,dc=org', 'proxypassword'),
            ServerEntry('127.0.0.1', 3891, 'dc=example,dc=org', 'cn=proxy,dc=example,dc=org', 'proxypassword'),
        ]

        # start server
        self.startServer(port=3890, server=AcceptBind)
        self.startServer(port=3891, server=UnresponsiveBind)

        # start proxy
        proxy = lambda: ProxyMerger(OneClientDatabase(client, servers), timeout=1)
        self.startServer(port=10389, server=proxy)

        # start client
        clientDef = self.startClient(port=10389, client=BindingClient(client.dn, client.password))
        clientDef.addCallback(self.fail)
        clientDef.addErrback(self.succeed)
        clientDef.addTimeout(5, reactor, onTimeoutCancel=lambda err, t: self.fail())

        # wait completion
        return clientDef

    def test_search_should_be_executed_on_all_servers(self):
        # config
        client = ClientEntry('cn=client,dc=example,dc=org', 'clientpassword')
        servers = [
            ServerEntry('127.0.0.1', 3890, 'dc=example,dc=org', 'cn=proxy,dc=example,dc=org', 'proxypassword'),
            ServerEntry('127.0.0.1', 3891, 'dc=example,dc=org', 'cn=proxy,dc=example,dc=org', 'proxypassword')
        ]

        # start server
        for s in servers:
            self.startServer(port=s.port, server=SimpleSearch)

        # start proxy
        proxy = lambda: ProxyMerger(OneClientDatabase(client, servers))
        self.startServer(port=10389, server=proxy)

        # start client
        clientDef = self.startClient(port=10389, client=SearchingClient('dc=example,dc=org', filter='(objectClass=*)'))

        def check_result(result):
            self.assertEqual(len(result), 2) # expecting two entries
            entry = result[0]
            self.assertEqual(list(entry.get("cn")), [b"Bob"])
            self.assertEqual(list(entry.get("sn")), [b"Bobby"])
            self.assertEqual(list(entry.get("mail")), [b"bob@example.com"])

        clientDef.addCallback(check_result)
        clientDef.addErrback(self.fail)

        # wait completion
        return clientDef
    
    def test_search_should_fail_when_one_server_is_unavailable(self):
        # config
        client = ClientEntry('cn=client,dc=example,dc=org', 'clientpassword')
        servers = [
            ServerEntry('127.0.0.1', 3890, 'dc=example,dc=org', 'cn=proxy,dc=example,dc=org', 'proxypassword'),
            ServerEntry('127.0.0.1', 3891, 'dc=example,dc=org', 'cn=proxy,dc=example,dc=org', 'proxypassword')
        ]

        # start server
        self.startServer(port=3890, server=SimpleSearch)
        self.startServer(port=3891, server=UnresponsiveSearch)

        # start proxy
        proxy = lambda: ProxyMerger(OneClientDatabase(client, servers), timeout=1)
        self.startServer(port=10389, server=proxy)

        # start client
        clientDef = self.startClient(port=10389, client=SearchingClient('dc=example,dc=org', filter='(objectClass=*)'))
        clientDef.addCallback(self.fail)
        clientDef.addErrback(self.succeed)
        clientDef.addTimeout(5, reactor, onTimeoutCancel=lambda err, t: self.fail())

        return clientDef
    
    def test_only_read_operations_should_be_allowed(self):
        # config
        client = ClientEntry('cn=client,dc=example,dc=org', 'clientpassword')
        servers = [
            ServerEntry('127.0.0.1', 3890, 'dc=example,dc=org', 'cn=proxy,dc=example,dc=org', 'proxypassword'),
            ServerEntry('127.0.0.1', 3891, 'dc=example,dc=org', 'cn=proxy,dc=example,dc=org', 'proxypassword')
        ]

        # start server
        for s in servers:
            self.startServer(port=s.port, server=AcceptBind)

        # start proxy
        proxy = lambda: ProxyMerger(OneClientDatabase(client, servers))
        self.startServer(port=10389, server=proxy)

        def _checkError(error):
            self.assertIsInstance(error.value, ldaperrors.LDAPUnwillingToPerform)
        # test Delete
        clientDel = self.startClient(port=10389, client=DeletingClient('cn=client,dc=example,dc=org'))
        clientDel.addBoth(_checkError)
        # test Modify
        clientMod = self.startClient(port=10389, client=ModifyingClient('cn=client,dc=example,dc=org'))
        clientMod.addBoth(_checkError)

        return defer.DeferredList([clientDel, clientMod])

    def test_request_should_fail_when_database_is_unavailable(self):
        # config
        client = ClientEntry('cn=client,dc=example,dc=org', 'clientpassword')
        servers = [
            ServerEntry('127.0.0.1', 3890, 'dc=example,dc=org', 'cn=proxy,dc=example,dc=org', 'proxypassword'),
            ServerEntry('127.0.0.1', 3891, 'dc=example,dc=org', 'cn=proxy,dc=example,dc=org', 'proxypassword')
        ]

        # start server
        self.startServer(port=3890, server=AcceptBind)
        self.startServer(port=3891, server=AcceptBind)

        # start proxy
        proxy = lambda: ProxyMerger(ErrorThrowDatabase(client, servers), timeout=1)
        self.startServer(port=10389, server=proxy)

        # start client
        clientDef = self.startClient(port=10389, client=BindingClient(client.dn, client.password))
        clientDef.addCallback(self.fail)
        clientDef.addErrback(self.succeed)
        clientDef.addTimeout(5, reactor, onTimeoutCancel=lambda err, t: self.fail())

        return clientDef

if __name__ == '__main__':
    unittest.main()