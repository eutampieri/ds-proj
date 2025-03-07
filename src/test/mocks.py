from twisted.internet import reactor, defer
from twisted.internet.defer import Deferred
from ldaptor.protocols import pureldap
from ldaptor.protocols.ldap.ldapserver import LDAPServer
from ldaptor.protocols.ldap import ldapsyntax
from ldaptor.protocols.ldap.ldapconnector import connectToLDAPEndpoint
from ldaptor.protocols.ldap.ldapclient import LDAPClient
from ldaptor.protocols.ldap.distinguishedname import DistinguishedName

### LDAP Client ###

class MockLDAPClient():
    """A base mock for a LDAP client."""
    def run(self, endpoint) -> Deferred:
        """Executes the query of this client."""
        pass

class BindingClient(MockLDAPClient):
    """A mock LDAP client that makes a bind request."""
    def __init__(self, dn: str, password: str):
        self.dn = dn
        self.password = password

    def bind(self, endpoint, dn: str, password: str) -> Deferred:
        d = connectToLDAPEndpoint(reactor, endpoint, LDAPClient)

        def _doBind(proto):
            baseEntry = ldapsyntax.LDAPEntry(client=proto, dn=DistinguishedName(dn))
            x = baseEntry.bind(password=password)
            return x
        
        d.addCallback(_doBind)
        return d

    def run(self, endpoint) -> Deferred:
        d = self.bind(endpoint, self.dn, self.password)
        d.addErrback(defer.logError)
        return d

class SearchingClient(MockLDAPClient):
    """A mock LDAP client that makes a search request."""
    def __init__(self, base_dn: str, filter: str):
        self.base_dn = base_dn
        self.filter = filter

    def search(self, endpoint, base_dn: str, filter: str) -> Deferred:
        d = connectToLDAPEndpoint(reactor, endpoint, LDAPClient)

        def _doSearch(proto):
            from ldaptor import ldapfilter
            searchFilter = ldapfilter.parseFilter(filter)
            baseEntry = ldapsyntax.LDAPEntry(client=proto, dn=DistinguishedName(base_dn))
            x = baseEntry.search(filterObject=searchFilter)
            return x
        
        d.addCallback(_doSearch)
        return d

    def run(self, endpoint) -> Deferred:
        d = self.search(endpoint, self.base_dn, self.filter)
        d.addErrback(defer.logError)
        return d


### LDAP Server ###

class MockLDAPServer(LDAPServer):
    """A base mock for a LDAP server. Needs to be extended with the wanted capabilities."""

class AcceptBind(MockLDAPServer):
    """A mock LDAP server that accepts all bind requests."""
    def handle_LDAPBindRequest(self, request, controls, reply):
        # Accept bind request
        return reply(pureldap.LDAPBindResponse(resultCode=0))
    
class RejectBind(MockLDAPServer):
    """A mock LDAP server that rejects all bind requests."""
    def handle_LDAPBindRequest(self, request, controls, reply):
        # Reject bind request (invalid credentials)
        return reply(pureldap.LDAPBindResponse(resultCode=49))
    
class UnresponsiveBind(MockLDAPServer):
    """A mock LDAP server that never replies to binf requests."""
    def handle_LDAPBindRequest(self, request, controls, reply):
        # Dont reply to bind request
        pass