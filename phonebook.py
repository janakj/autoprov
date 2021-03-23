import json

# [001565f4f9e1] Received provisioning request, vendor yealink, model W52P, firmware 25.81.0.30
# [001565f4f9e1] Sending provisioning URL http://192.168.1.213:8080/yealink/W52P/ to device
# [001565f4f9e1] Device acknowledged provisioning URL
# 192.168.1.160 - - [21/Sep/2018 17:01:37] "GET /yealink/W52P/001565f4f9e1.boot HTTP/1.1" 404 -
# 192.168.1.160 - - [21/Sep/2018 17:01:37] "GET /yealink/W52P/y000000000000.boot HTTP/1.1" 404 -
# 192.168.1.160 - - [21/Sep/2018 17:01:37] "GET /yealink/W52P/y000000000025.cfg HTTP/1.1" 200 -
# 192.168.1.160 - - [21/Sep/2018 17:01:45] "GET /static/yealink/W52P/base/25.81.0.30.rom HTTP/1.1" 200 -
# New assignment "001565f4f9e1" -> "RTO 1"
# 192.168.1.160 - - [21/Sep/2018 17:01:48] "GET /yealink/W52P/001565f4f9e1.cfg HTTP/1.1" 200 -
# 192.168.1.160 - - [21/Sep/2018 17:01:56] "GET /static/yealink/W52P/handset/26.73.0.30.rom HTTP/1.1" 200 -
# 192.168.1.160 - - [21/Sep/2018 17:01:56] "GET /static/yealink/W52P/handset/26.73.0.30.rom HTTP/1.1" 200 -

# [001565f4f895] Received provisioning request, vendor yealink, model W52P, firmware 25.81.0.10
# [001565f4f895] Sending provisioning URL http://192.168.1.213:8080/yealink/W52P/ to device
# [001565f4f895] Device acknowledged provisioning URL
# 192.168.1.185 - - [21/Sep/2018 17:04:16] "GET /yealink/W52P/001565f4f895.boot HTTP/1.1" 404 -
# 192.168.1.185 - - [21/Sep/2018 17:04:16] "GET /yealink/W52P/y000000000000.boot HTTP/1.1" 404 -
# 192.168.1.185 - - [21/Sep/2018 17:04:16] "GET /yealink/W52P/y000000000025.cfg HTTP/1.1" 200 -
# 192.168.1.185 - - [21/Sep/2018 17:04:26] "GET /static/yealink/W52P/base/25.81.0.30.rom HTTP/1.1" 200 -
# [001565f4f895] Received provisioning request, vendor yealink, model W52P, firmware 25.81.0.30
# [001565f4f895] Sending provisioning URL http://192.168.1.213:8080/yealink/W52P/ to device
# [001565f4f895] Device acknowledged provisioning URL
# 192.168.1.185 - - [21/Sep/2018 17:07:58] "GET /yealink/W52P/001565f4f895.boot HTTP/1.1" 404 -
# 192.168.1.185 - - [21/Sep/2018 17:07:58] "GET /yealink/W52P/y000000000000.boot HTTP/1.1" 404 -
# 192.168.1.185 - - [21/Sep/2018 17:07:58] "GET /yealink/W52P/y000000000025.cfg HTTP/1.1" 200 -
# 192.168.1.185 - - [21/Sep/2018 17:08:06] "GET /static/yealink/W52P/base/25.81.0.30.rom HTTP/1.1" 200 -
# New assignment "001565f4f895" -> "RTO 2"
# 192.168.1.185 - - [21/Sep/2018 17:08:09] "GET /yealink/W52P/001565f4f895.cfg HTTP/1.1" 200 -
# 192.168.1.185 - - [21/Sep/2018 17:08:19] "GET /static/yealink/W52P/handset/26.73.0.30.rom HTTP/1.1" 200 -
# 192.168.1.185 - - [21/Sep/2018 17:08:20] "GET /static/yealink/W52P/handset/26.73.0.30.rom HTTP/1.1" 200 -


class PhoneBook(object):
    def __init__(self, lease_file):
        self.lease_file = lease_file

    def load_leases(self):
        try:
            print('Loading leases from %s' % self.lease_file)
            with open(self.lease_file) as f:
                data = json.loads(f.read())
                print('Loaded %d leases' % len(data.keys()))
                return data
        except FileNotFoundError:
            print('No lease file found, creating a new empty one')
            return dict()
        except ValueError:
            print('Found malformed lease file, creating a new empty one')
            return dict()

    def save_leases(self, data):
        print('Saving %d leases to file %s' % (len(data.keys()), self.lease_file))
        with open(self.lease_file, 'w') as f:
            f.write(json.dumps(data, indent=4, sort_keys=True))

    def find_unassigned_base_station_prefix(self, leases):
        for prefix in range(0, 10):
            used = False
            for mac, assigned_prefix in leases.items():
                if assigned_prefix == str(prefix):
                    used = True
                    break
            if not used:
                return str(prefix)
        return None

    def assign(self, mac):
        mac = mac.lower()
        leases = self.load_leases()

        try:
            p = leases[mac]
            print('Found existing lease "%s" -> "%s"' % (mac, p))
            return p
        except KeyError:
            prefix = self.find_unassigned_base_station_prefix(leases)

        if prefix is None:
            raise ValueError('No free base station prefixes found')

        print('Assigning "%s" -> "%s"' % (mac, prefix))

        leases[mac] = prefix
        self.save_leases(leases)

        return prefix
