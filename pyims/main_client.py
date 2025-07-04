import logging
import time

from pyims.nio.inet import InetAddress
from pyims.sip.client import Client, Account

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s', handlers=[logging.StreamHandler()])


local_address = InetAddress('172.22.0.1', 50601)
pcscf_address = InetAddress('172.22.0.21', 5060)
account = Account(
    '001', '001',
    '001011234567895',
    '0011111111111112',
    sim_opc='001122334455667788',
    sim_amf='8000'
)
# msisdn = 8801500121121

client = Client(local_address, pcscf_address, account)
try:
    client.register()

    while True:
        time.sleep(10)
finally:
    client.close()
