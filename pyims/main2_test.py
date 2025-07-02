from pyims.sip.sip_types import Version, Method
from pyims.sip.headers import CSeq, Via, From, To, CallID, CustomHeader
from pyims.sip.message import RequestMessage
from pyims.sip.transport import TcpTransport
from pyims.sip.client import Client


client = Client(TcpTransport('172.22.0.1', 50601, '172.22.0.21', 5060))
try:
    resp = client.request(RequestMessage(
        Version.VERSION_2,
        Method.REGISTER,
        'sip:ims.mnc001.mcc001.3gppnetwork.org',
        headers=[
            From(uri='sip:001011234567895@ims.mnc001.mcc001.3gppnetwork.org', tag=''),
            To(uri='sip:001011234567895@ims.mnc001.mcc001.3gppnetwork.org'),
            CSeq(Method.REGISTER, 1),
            CallID('1-119985@172.22.0.1'),
            Via(Version.VERSION_2, 'TCP', '172.22.0.1:5060', branch='z9hG4bK-119985-1-0-reg'),
            CustomHeader('Max-Forwards', '70'),
            CustomHeader('Expires', '1800'),
            CustomHeader('Supported', 'path'),
            CustomHeader('P-Access-Network-Info', '3GPP-E-UTRAN-FDD; utran-cell-id-3gpp=001010001000019B'),
            CustomHeader('Allow', ','.join([method.value for method in list(Method)])),
            CustomHeader('Content-Length', '0')
        ]
    ))
    print(resp)
finally:
    client.close()
