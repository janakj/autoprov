import os
import uuid
import socket
import struct
import netifaces


PROVISIONING_URL = os.environ['PROVISIONING_URL']
NODE_NAME = os.environ['NODE_NAME']
INTERFACES = [s for s in os.environ.get('INTERFACES', '').split(',') if s]
DEBUG = os.environ.get('DEBUG', None)


def parse_subscribe(request):
    '''
    SUBSCRIBE sip:MAC001565f4f9e1@224.0.1.75 SIP/2.0.
    Via: SIP/2.0/UDP 10.1.3.239:5059;branch=z9hG4bK1536537630.
    From: <sip:MAC001565f4f9e1@224.0.1.75>;tag=1536537630.
    To: <sip:MAC001565f4f9e1@224.0.1.75>.
    Call-ID: 1536537630@10.1.3.239.
    CSeq: 1 SUBSCRIBE.
    Contact: <sip:MAC001565f4f9e1@10.1.3.239:5059>.
    Max-Forwards: 70.
    User-Agent: Yealink W52P 25.81.0.10.
    Expires: 0.
    Event: ua-profile;profile-type="device";vendor="yealink";model="W52P";version="25.81.0.10".
    Accept: application/url.
    Content-Length: 0.
    '''

    headers = dict()

    lines = request.split('\r\n')

    try:
        method, uri, proto = lines[0].strip().split(' ')
    except:
        return None

    if method != 'SUBSCRIBE':
        return None

    if proto != 'SIP/2.0':
        return None

    if uri[:7] != 'sip:MAC':
        return None

    if uri[20:] != '224.0.1.75':
        return None

    mac = uri[7:7+12].lower()

    for line in lines[1:]:
        sep = line.find(':')
        if sep == -1:
            continue

        name = line[:sep].strip().lower()
        value = line[sep+1:].strip()
        headers[name] = value

    ua_ip = headers['via'][12:].split(';')[0].split(':')[0]
    ua_port = int(headers['via'][12:].split(';')[0].split(':')[1])

    kvargs = headers['event'].split(';')
    vendor = kvargs[2].split('=')[1][1:-1]
    model = kvargs[3].split('=')[1][1:-1]
    fw_version = kvargs[4].split('=')[1][1:-1]

    return (mac, (ua_ip, ua_port), vendor, model, fw_version, headers)


def parse_200ok(response):
    lines = response.split('\r\n')

    try:
        proto, code, reason = lines[0].strip().split(' ')
    except:
        return False

    if proto != 'SIP/2.0':
        return False

    if code != '200':
        return False

    return True


def make_200ok(me, tag, headers):
    template = '''SIP/2.0 200 OK\r
Via: SIP/2.0/UDP {ip}:{port};branch={branch}\r
From: {from_}\r
To: {to};tag={tag}\r
Call-ID: {callid}\r
Contact: <sip:{ip}:{port}>\r
CSeq: {cseq}\r
Expires: 0\r
Content-Length: 0\r
\r'''

    return template.format(
        ip=me[0],
        port=me[1],
        tag=tag,
        branch=headers['via'].split(';')[1].split('=')[1],
        to = headers['to'],
        from_ = headers['from'],
        callid = headers['call-id'],
        cseq = headers['cseq'])


def make_notify(me, url, tag, subscribe_headers):
    template = '''NOTIFY {contact_uri} SIP/2.0\r
To: {to}\r
From: {from_};tag={tag}\r
Via: SIP/2.0/UDP {ip}:{port};branch={branch}\r
Max-Forwards: 70\r
Contact: <sip:{ip}:{port}>\r
Call-ID: {callid}\r
CSeq: {cseq} NOTIFY\r
Subscription-State: terminated;reason=noresource\r
Event: ua-profile\r
Content-Type: application/url\r
Content-Length: {clen}\r
\r
{url}'''

    return template.format(
        contact_uri=subscribe_headers['contact'][1:-1],
        to=subscribe_headers['from'],
        from_=subscribe_headers['to'],
        tag=tag,
        ip=me[0],
        port=me[1],
        branch='z9hG4bK1539375389247630',
        callid=subscribe_headers['call-id'],
        cseq=2,
        clen=len(url),
        url=url)


def sip_pnp(url):
    print('Starting SIP PnP provisioning agent')
    print('Provisioning server URL: %s' % url)

    print('Binding socket UDP:224.0.1.75:5060')
    mcast_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    mcast_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    mcast_sock.bind(('224.0.1.75', 5060))

    print('Binding socket UDP:0.0.0.0:5062')
    ucast_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    ucast_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    ucast_sock.bind(('0.0.0.0', 5062))

    if len(INTERFACES) == 0:
        print('Joining multicast group 224.0.1.75')
        data = struct.pack('4sl', socket.inet_aton('224.0.1.75'), socket.INADDR_ANY)
        mcast_sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, data)
    else:
        for ifname in INTERFACES:
            print('Joining multicast group 224.0.1.75 on interface %s' % ifname)
            addr = netifaces.ifaddresses(ifname)[netifaces.AF_INET][0]['addr']
            data = struct.pack('4s4s', socket.inet_aton('224.0.1.75'), socket.inet_aton(addr))
            mcast_sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, data)


    while True:
        request = mcast_sock.recv(65536).decode('utf-8')
        if DEBUG is not None:
            print('Got multicast packet')

        data = parse_subscribe(request)
        if data is None:
            if DEBUG is not None:
                print("Couldn't parse packet, skipping")
            continue

        mac, ua, vendor, model, firmware, headers = data

        print("[%s] Received SUBSCRIBE, vendor %s, model %s, firmware %s"
              % (mac, vendor, model, firmware))

        tag = str(uuid.uuid4())
        ucast_sock.connect(ua)
        ucast_sock.settimeout(5)
        me = ucast_sock.getsockname()

        print('[%s] Sending 200 OK in response to SUBSCRIBE' % mac)
        ucast_sock.send(make_200ok(me, tag, headers).encode('utf-8'))

        u = '%s/%s/%s/%s/%s/%s/%s' % (url,
            NODE_NAME.lower(),
            vendor.lower(),
            model.lower(),
            ua[0].lower(),
            mac.lower(),
            firmware.lower())
        print('[%s] Sending NOTIFY with provisioning URL %s' % (mac, u))
        ucast_sock.send(make_notify(me, u, tag, headers).encode('utf-8'))


if __name__ == '__main__':
    sip_pnp(PROVISIONING_URL)
