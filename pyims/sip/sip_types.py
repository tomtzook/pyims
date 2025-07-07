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
    RINGING = (180, 'Ringing')
    CALL_BEING_FORWARDED = (181, 'Call is Being Forwarded')
    QUEUED = (182, 'Queued')
    SESSION_PROGRESS = (183, 'Session Progress')
    EARLY_DIALOG_TERMINATED = (199, 'Early Dialog Terminated')
    OK = (200, 'OK')
    ACCEPTED = (202, 'Accepted')
    NO_NOTIFICATION = (204, 'No Notification')
    MULTIPLE_CHOICES = (300, 'Multiple Choices')
    MOVED_PERMANENTLY = (301, 'Moved Permanently')
    MOVED_TEMPORARILY = (302, 'Moved Temporarily')
    USE_PROXY = (305, 'Use Proxy')
    ALTERNATIVE_SERVICE = (380, 'Alternative Service')
    BAD_REQUEST = (400, 'Bad Request')
    UNAUTHORIZED = (401, 'Unauthorized')
    PAYMENT_REQUIRED = (402, 'Payment Required')
    FORBIDDEN = (403, 'Forbidden')
    NOT_FOUND = (404, 'Not Found')
    METHOD_NOT_ALLOWED = (405, 'Method Not Allowed')
    NOT_ACCEPTABLE = (406, 'Not Acceptable')
    PROXY_AUTHENTICATION_REQUIRED = (407, 'Proxy Authentication Required')
    REQUEST_TIMEOUT = (408, 'Request Timeout')
    CONFLICT = (409, 'Conflict')
    GONE = (409, 'Gone')
    LENGTH_REQUIRED = (411, 'Length Required')
    CONDITIONAL_REQUEST_FALIED = (412, 'Conditional Request Failed')
    REQUEST_ENTITY_TOO_LARGE = (413, 'Request Entity Too Large')
    REQUEST_URI_TOO_LONG = (414, 'Request URI Too Long')
    UNSUPPORTED_MEDIA_TYPE = (415, 'Unsupported Media Type')
    UNSUPPORTED_URI_SCHEME = (416, 'Unsupported URI Scheme')
    UNKNOWN_RESOURCE_PRIORITY = (417, 'Unknown Resource Priority')
    BAD_EXTENSION = (420, 'Bad Extension')
    EXTENSION_REQUIRED = (421, 'Extension Required')
    SESSION_INTERVAL_TOO_SMALL = (422, 'Session Interval Too Small')
    INTERVAL_TOO_BRIEF = (423, 'Interval Too Brief')
    BAD_LOCATION_INFORMATION = (424, 'Bad Location Information')
    BAD_ALERT_INFORMATION = (424, 'Bad Alert Information')
    BAD_ALERT_MESSAGE = (425, 'Bad Alert Message')
    USE_IDENTITY_HEADER = (428, 'Use Identity Header')
    PROVIDE_REFERRER_IDENTITY = (429, 'Provide Referrer Identity')
    FLOW_FAILED = (430, 'Flow Failed')
    ANONYMITY_DISALLOWED = (433, 'Anonymity Disallowed')
    BAD_IDENTITY_INFO = (436, 'Bad Identity Info')
    UNSUPPORTED_CERTIFICATE = (437, 'Unsupported Certificate')
    INVALID_IDENTITY_HEADER = (438, 'Invalid Identity Header')
    FIRST_HOP_LACKS_OUTBOUND_SUPPORT = (439, 'First Hop Lacks Outbound Support')
    MAX_BREADTH_EXCEEDED = (440, 'Max-Breadth Exceeded')
    BAD_INFO_PACKAGE = (469, 'Bad Info Package')
    CONSENT_NEEDED = (470, 'Consent Needed')
    TEMPORARILY_UNAVAILABLE = (480, 'Temporarily Unavailable')
    CALL_TRANSACTION_DOES_NOT_EXIST = (481, 'Call/Transaction Does Not Exist')
    LOOP_DETECTED = (482, 'Loop Detected')
    TOO_MANY_HOPS = (483, 'Too Many Hops')
    ADDRESS_INCOMPLETE = (484, 'Address Incomplete')
    AMBIGUOUS = (485, 'Ambiguous')
    BUSY_HERE = (486, 'Busy Here')
    REQUEST_TERMINATED = (487, 'Request Terminated')
    NOT_ACCEPTABLE_HERE = (488, 'Not Acceptable Here')
    BAD_EVENT = (489, 'Bad Event')
    REQUEST_PENDING = (491, 'Request Pending')
    UNDECIPHERABLE = (493, 'Undecipherable')
    SECURITY_AGREEMENT_REQUIRED = (494, 'Security Agreement Required')
    INTERNAL_SERVER_ERROR = (500, 'Internal Server Error')
    NOT_IMPLEMENTED = (501, 'Not Implemented')
    BAD_GATEWAY = (502, 'Bad Gateway')
    SERVICE_UNAVAILABLE = (503, 'Service Unavailable')
    SERVER_TIMEOUT = (504, 'Server Time-out')
    VERSION_NOT_SUPPORTED = (505, 'Version Not Supported')
    MESSAGE_TOO_LARGE = (513, 'Message Too Large')
    PUSH_NOTIFICATION_NOT_SUPPORTED = (555, 'Push Notification Service Not Supported')
    PRECONDITION_FAILURE = (580, 'Precondition Failure')
    BUSY_EVERYWHERE = (600, 'Busy Everywhere')
    DECLINE = (603, 'Decline')
    DOES_NOT_EXIST_ANYWHERE = (604, 'Does Not Exist Anywhere')
    NOT_ACCEPTABLE_GLOBAL = (606, 'Not Acceptable')
    UNWANTED = (607, 'Unwanted')
    REJECTED = (608, 'Rejected')


class AuthenticationScheme(enum.Enum):
    DIGEST = 'Digest'


class AuthenticationAlgorithm(enum.Enum):
    AKA = 'AKAv1-MD5'
    MD5 = 'MD5'


Status = namedtuple('Status', 'code,description')
User = namedtuple('User', 'username,host')

METHODS = [method.name for method in list(Method)]
VERSIONS_BY_STR = {version.value: version for version in list(Version)}
STATUS_FROM_NUMBER = {status.value[0]: status for status in list(StatusCode)}
AUTH_SCHEME_BY_STR = {scheme.value: scheme for scheme in list(AuthenticationScheme)}
AUTH_ALGO_BY_STR = {algo.value: algo for algo in list(AuthenticationAlgorithm)}
