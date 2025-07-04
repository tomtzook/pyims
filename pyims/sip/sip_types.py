import enum
from collections import namedtuple


class MessageType(enum.Enum):
    REQUEST = 'request'
    RESPONSE = 'response'


class Method(enum.Enum):
    INVITE = 'INVITE'
    ACK = 'ACK'
    BYE = 'BYE'
    CANCEL = 'CANCEL'
    UPDATE = 'UPDATE'
    INFO = 'INFO'
    SUBSCRIBE = 'SUBSCRIBE'
    NOTIFY = 'NOTIFY'
    REFER = 'REFER'
    MESSAGE = 'MESSAGE'
    OPTIONS = 'OPTIONS'
    REGISTER = 'REGISTER'


class Version(enum.Enum):
    VERSION_2 = "SIP/2.0"


class StatusCode(enum.Enum):
    TRYING = (100, 'Trying')
    OK = (200, 'OK')
    UNAUTHORIZED = (401, 'Unauthorized')
    FORBIDDEN = (403, 'Forbidden')
    INTERNAL_SERVER_ERROR = (500, 'Internal Server Error')
    SERVER_TIMEOUT = (504, 'Server Time-out')
    DOES_NOT_EXIST_ANYWHERE = (604, 'Does Not Exist Anywhere')


class AuthenticationScheme(enum.Enum):
    DIGEST = 'Digest'


class AuthenticationAlgorithm(enum.Enum):
    AKA = 'AKAv1-MD5'
    MD5 = 'MD5'


Status = namedtuple('Status', 'code,description')

METHODS = [method.name for method in list(Method)]
VERSIONS_BY_STR = {version.value: version for version in list(Version)}
STATUS_FROM_NUMBER = {status.value[0]: status for status in list(StatusCode)}
AUTH_SCHEME_BY_STR = {scheme.value: scheme for scheme in list(AuthenticationScheme)}
AUTH_ALGO_BY_STR = {algo.value: algo for algo in list(AuthenticationAlgorithm)}
