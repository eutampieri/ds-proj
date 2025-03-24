from pymongo import MongoClient
DB_NAME = "ldap-proxy-database"

# DB entry of a ldap server
class ServerEntry():
    def __init__(self, ip, port, base_dn, bind_dn, bind_password, tls=False):
        self.ip = ip
        self.port = port
        self.base_dn = base_dn
        self.bind_dn = bind_dn
        self.bind_password = bind_password
        self.tls = tls

    def to_object(self):
        return {
            "ip": self.ip,
            "port": self.port,
            "base_dn": self.base_dn,
            "bind_dn": self.bind_dn,
            "bind_password": self.bind_password,
            "tls": self.tls
        }
    
# DB entry of a user/admin
class UserEntry():
    def __init__(self, user, password, is_admin):
        self.user = user
        self.password = password # da cambiare, va salata
        self.is_admin = is_admin
    
    def to_object(self):
        return {
            "user": self.user,
            "password": self.password,
            "is_admin": self.is_admin,
        }

# DB entry of a client
class ClientEntry():
    def __init__(self, dn, password):
        self.dn = dn
        self.password = password # da cambiare, va salata

    def to_object(self):
        return {
            "dn": self.dn,
            "password": self.password,
        }

# DB utility class
class ProxyDatabase():
    def __init__(self, address, port):
        self.client = MongoClient(address, port)
        self.db = self.client[DB_NAME]
        
    def put_server(self, server: ServerEntry) -> None:
        self.db["servers"].insert_one(server.to_object())

    def get_servers(self) -> list[ServerEntry]:
        return [ServerEntry(ip=i["ip"], base_dn=i["base_dn"], bind_dn=i["bind_dn"], bind_password=i["bind_password"],
                               port=i["port"], tls=i["tls"]) for i in self.db["servers"].find()]
    
    def put_user(self, user: UserEntry) -> None:
        self.db["users"].insert_one(user.to_object())

    def get_admins(self) -> list[UserEntry]:
        return [UserEntry(i["user"], i["password"], True) for i in self.db["users"].find({"is_admin": True})]
    
    def get_users(self) -> list[UserEntry]:
        return [UserEntry(i["user"], i["password"], i["is_admin"]) for i in self.db["users"].find()]
    
    def put_client(self, client: ClientEntry) -> None:
        self.db["clients"].insert_one(client.to_object())

    def get_clients(self) -> list[ClientEntry]:
        return [ClientEntry(i["dn"], i["password"]) for i in self.db["clients"].find()]

    # authenticate a client and return it. Return None if not authorized
    def get_authenticated_client(self, client_dn, client_auth) -> ClientEntry | None:
        clients = self.get_clients()
        for u in clients:
            if u.dn == client_dn and u.password == client_auth:
                return u
        return None