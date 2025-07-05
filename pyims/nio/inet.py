

class InetAddress(object):

    def __init__(self, ip: str, port: int):
        self.ip = ip
        self.port = port

    def __eq__(self, other):
        if not isinstance(other, InetAddress):
            return False
        return self.ip == other.ip and self.port == other.port

    def __str__(self):
        return f"{self.ip}:{self.port}"

    def __repr__(self):
        return self.__str__()
