import enum


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


class Status(enum.Enum):
    TRYING = (100, 'Trying')
    OK = (200, 'OK')
    UNAUTHORIZED = (401, 'Unauthorized')


class AuthenticationScheme(enum.Enum):
    DIGEST = 'Digest'


class AuthenticationAlgorithm(enum.Enum):
    AKA = 'AKAv1-MD5'


METHODS = [method.name for method in list(Method)]
VERSIONS_BY_STR = {version.value: version for version in list(Version)}
STATUS_FROM_NUMBER = {status.value[0]: status for status in list(Status)}
AUTH_SCHEME_BY_STR = {scheme.value: scheme for scheme in list(AuthenticationScheme)}
AUTH_ALGO_BY_STR = {algo.value: algo for algo in list(AuthenticationAlgorithm)}
