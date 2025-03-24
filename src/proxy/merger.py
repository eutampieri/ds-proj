import ldaptor.protocols.pureldap
from twisted.internet import protocol, defer, reactor
from ldaptor.config import LDAPConfig
from ldaptor.protocols.ldap import ldapclient, merger, ldaperrors
from proxy.proxydatabase import ProxyDatabase, ServerEntry, UserEntry
from ldaptor.protocols import pureldap

class TimeoutLDAPClient(ldapclient.LDAPClient):
    """LDAP Client that can be set with a timeout for connection"""
    def __init__(self, timeout):
        self.timeout = timeout
        super().__init__()

    def __on_timeout(self, err, time):
        raise ldaperrors.LDAPTimeLimitExceeded(f"LDAP request timed out after {time} seconds")
    
    def send(self, op, controls=None):
        d = super().send(op, controls)
        d.addTimeout(self.timeout, reactor, self.__on_timeout)
        return d
    
    def send_multiResponse(self, op, handler, *args, **kwargs):
        d = super().send_multiResponse(op, handler, *args, **kwargs)
        d.addTimeout(self.timeout, reactor, self.__on_timeout)
        return d
    
    def send_multiResponse_ex(self, op, controls=None, handler=None, *args, **kwargs):
        d = super().send_multiResponse_ex(self, op, controls, handler, *args, **kwargs)
        d.addTimeout(self.timeout, reactor, self.__on_timeout)
        return d
    
class DeferredRequestAggregator():
    """Deferred builder that simplifies the creation of DeferredList for replying to LDAPRequests."""
    def __init__(self, reply, LDAPReplyMessageType: pureldap.LDAPProtocolResponse):
        """Create an empty builder. Define the `reply` method and the `msg type` for response."""
        self.requests = []
        self.callbacks = []
        self.msg_type = LDAPReplyMessageType
        self.reply = reply

    def append(self, request: defer.Deferred):
        """Add a request to the list."""
        self.requests.append(request)

    def addErrback(self, errback):
        """Add an errback to the final DeferredList."""
        self.callbacks.append((False, errback))

    def addCallback(self, callback):
        """Add a callback to the final DeferredList."""
        self.callbacks.append((True, callback))

    def build(self) -> defer.DeferredList:
        """Generate the DeferredList from the requests added. It automagically replies on error, so no management is needed."""
        deferred = defer.DeferredList(self.requests, fireOnOneErrback=True, consumeErrors=True)
        for c in self.callbacks:
            if c[0]:
                deferred.addCallback(c[1])
            else:
                deferred.addErrback(c[1])
        def _replyWithError(failure): # failure is a Failure(FirstFailure)
            f = failure.value.subFailure
            r = self.msg_type(resultCode=f.value.resultCode)
            [self.reply(r) for c in self.requests]
        deferred.addErrback(_replyWithError)
        return deferred

class ProxyMerger(merger.MergedLDAPServer):
    """LDAP Proxy that redirects and aggregates all bind and search requests."""

    INVALID_CREDENTIALS = 49
    SERVER_DOWN = 81

    def __init__(self, database: ProxyDatabase, timeout=30):
        self.timeout = timeout
        self.protocol = lambda: TimeoutLDAPClient(timeout=timeout)
        self.allowed_operations = (pureldap.LDAPBindRequest, pureldap.LDAPSearchRequest)
        self.database = database
        try:
            creds, configs, tsl = self._fetchConfigs()
            self.credentials = creds
            super().__init__(configs, tsl)
        except:
            raise ConnectionError('Could not access the database for initialization.')

    def handle_LDAPBindRequest(self, request, controls, reply):
        def _authenticate(ignored=None):
            return self.authenticate_client(request.dn.decode("utf-8"), request.auth.decode("utf-8"))
        
        def _handle_bind_request(auth_client):
            if auth_client is None:
                # Invalid credentials
                [reply(pureldap.LDAPBindResponse(self.INVALID_CREDENTIALS)) for c in self.clients]
                
            else:
                # Client registered: binding with own credentials
                # for each client, send a bind request but with the credentials of the proxy
                builder = DeferredRequestAggregator(reply, pureldap.LDAPBindResponse)
                for client, creds in zip(self.clients, self.credentials):
                    ldap_bind_request = pureldap.LDAPBindRequest(version=3, dn=creds[0], auth=creds[1])
                    d = client.send(ldap_bind_request)
                    builder.append(d)

                def _pickWorstResult(result):
                    r = max(result, key=lambda r: r[1].resultCode)
                    return r[1]
                def _replyWithSuccess(result): # result is [(bool, result), (bool, result), ...]
                    r = _pickWorstResult(result)
                    [reply(r) for c in self.clients]

                builder.addCallback(_replyWithSuccess)
                return builder.build()
            
        def _replyWithServerError(failure):
            r = pureldap.LDAPBindResponse(self.SERVER_DOWN)
            reply(r)
            [reply(r) for c in self.clients]
        
        d = self.loadConfigs()
        d.addCallback(_authenticate)
        d.addCallback(_handle_bind_request)
        d.addErrback(_replyWithServerError)
        return d
        
    def handle_LDAPSearchRequest(self, request, controls, reply):
        def _handle_search_request(ignored=None):
            builder = DeferredRequestAggregator(reply, pureldap.LDAPSearchResultDone)
            for client in self.clients:
                d = client.send_multiResponse(request, self._gotResponse, reply)
                builder.append(d)
            return builder.build()
        
        def _replyWithServerError(failure):
            r = pureldap.LDAPSearchResultDone(self.SERVER_DOWN)
            [reply(r) for c in self.clients]
    
        d = self.loadConfigs()
        d.addCallback(_handle_search_request)
        d.addErrback(_replyWithServerError)
        return d

    def _ldap_config_from_db_entry(self, config: ServerEntry):
        return (
            LDAPConfig(serviceLocationOverrides={"": (config.ip, config.port)}),
            (config.bind_dn, config.bind_password)
        )
    
    def _fetchConfigs(self):
        configs = self.database.get_servers()
        c = [self._ldap_config_from_db_entry(i) for i in configs]
        proxyCredentials = [i[1] for i in c]
        proxyConfigs = [i[0] for i in c]
        proxyTSL = [c.tls for c in configs]
        return (proxyCredentials, proxyConfigs, proxyTSL)
    
    def loadConfigs(self) -> defer.Deferred:
        """Load the proxy configuration. Return a deferred that fires when completed."""
        def _load(ignored=None):
            creds, configs, tsl = self._fetchConfigs()
            self.credentials = creds
            self.configs = configs
            self.use_tls = tsl

        d = defer.succeed(None)
        d.addCallback(_load)
        d.addTimeout(self.timeout, reactor)
        return d

    # authenticate a user. Return None if not authorized
    def authenticate_client(self, dn, auth) -> defer.Deferred:
        d = defer.succeed(None)
        d.addCallback(lambda _: self.database.get_authenticated_client(dn, auth))
        d.addTimeout(self.timeout, reactor)
        return d