from sip.sip_types import Version, Method, StatusCode
from sip.headers import CSeq, CallID, Via, From, To
from sip.parser import parse
from sip.composer import compose_request, compose_response


a = """REGISTER sip:ims.mnc001.mcc001.3gppnetwork.org SIP/2.0
From: <sip:001011234567895@ims.mnc001.mcc001.3gppnetwork.org>;tag=4130282085
To: <sip:001011234567895@ims.mnc001.mcc001.3gppnetwork.org>
CSeq: 909056609 REGISTER
Call-ID: 4130282081_47464792@192.168.101.2
Via: SIP/2.0/UDP 192.168.101.2:5060;branch=z9hG4bK3987742761
Max-Forwards: 70
P-Access-Network-Info: 3GPP-E-UTRAN-FDD; utran-cell-id-3gpp=001010001000019B
Content-Length: 0
Authorization: Digest uri="sip:ims.mnc001.mcc001.3gppnetwork.org",username="001011234567895@ims.mnc001.mcc001.3gppnetwork.org",response="",realm="ims.mnc001.mcc001.3gppnetwork.org",nonce=""
Expires: 600000
Supported: path
Allow: INVITE,BYE,CANCEL,ACK,NOTIFY,UPDATE,PRACK,INFO,MESSAGE,OPTIONS
Contact: <sip:192.168.101.2:5060>;+sip.instance="<urn:gsma:imei:86728703-952237-0>";+g.3gpp.icsi-ref="urn%3Aurn-7%3A3gpp-service.ims.icsi.mmtel";+g.3gpp.smsip;video;+g.3gpp.accesstype="cellular2"
""".replace('\n', '\r\n')

b = """"SIP/2.0 100 Trying
From: <sip:001011234567895@ims.mnc001.mcc001.3gppnetwork.org>;tag=4130282085
To: <sip:001011234567895@ims.mnc001.mcc001.3gppnetwork.org>
CSeq: 909056609 REGISTER
Call-ID: 4130282081_47464792@192.168.101.2
Via: SIP/2.0/UDP 192.168.101.2:5060;branch=z9hG4bK3987742761
Server: TelcoSuite Proxy-CSCF
Content-Length: 0
"""

"""
WWW-Authenticate: Digest realm="ims.mnc001.mcc001.3gppnetwork.org", nonce="8SA0p/qltIMlBqyAM/vqAFr2Rj1SH4AAMadojvfm1sU=", algorithm=AKAv1-MD5, ck="b12bd6d3bf809a6cf001a58187353060", ik="66cb51e13b70780e328e43ea52951d3f", qop="auth,auth-int"
"""

c = """SIP/2.0 401 Unauthorized - Challenging the UE
From: <sip:001011234567895@ims.mnc001.mcc001.3gppnetwork.org>;tag=4130282085
To: <sip:001011234567895@ims.mnc001.mcc001.3gppnetwork.org>;tag=a35a5806d6040414c4d26ea88c1e71a0-ec26680d
CSeq: 909056609 REGISTER
Call-ID: 4130282081_47464792@192.168.101.2
Via: SIP/2.0/UDP 192.168.101.2:5060;rport=5060;branch=z9hG4bK3987742761
WWW-Authenticate: Digest realm="ims.mnc001.mcc001.3gppnetwork.org", nonce="8SA0p/qltIMlBqyAM/vqAFr2Rj1SH4AAMadojvfm1sU=", algorithm=AKAv1-MD5, ck="b12bd6d3bf809a6cf001a58187353060", ik="66cb51e13b70780e328e43ea52951d3f", qop="auth,auth-int"
Path: <sip:term@pcscf.ims.mnc001.mcc001.3gppnetwork.org;lr>
Server: Kamailio S-CSCF
Content-Length: 0
""".replace('\n', '\r\n')

print(parse(c))

print(compose_request(
    Version.VERSION_2,
    Method.REGISTER,
    'sip:ims.mnc001.mcc001.3gppnetwork.org',
    '',
    headers=[
        CSeq(Method.REGISTER, 1),
        From(uri='sip:001011234567895@ims.mnc001.mcc001.3gppnetwork.org'),
        To(uri='sip:001011234567895@ims.mnc001.mcc001.3gppnetwork.org')
    ]
))

print(compose_response(
    Version.VERSION_2,
    StatusCode.OK,
    headers=[
        CSeq(Method.REGISTER, 1),
        From(uri='sip:001011234567895@ims.mnc001.mcc001.3gppnetwork.org'),
        To(uri='sip:001011234567895@ims.mnc001.mcc001.3gppnetwork.org')
    ]
))
