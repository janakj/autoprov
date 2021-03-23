import os
import sys
import csv
import json
from flask import Flask, abort, send_from_directory, url_for, request
from flask_mako import MakoTemplates, render_template
from phonebook import PhoneBook


ACCOUNTS = os.environ['ACCOUNTS']
CONFIG = os.environ.get('CONFIG', '/data/config.json')
LEASES = os.environ.get('LEASES', '/data/leases.json')
NUMBER_PREFIX = os.environ.get('NUMBER_PREFIX', '')


def get_password(username):
    print('Loading accounts from %s' % ACCOUNTS)
    with open(ACCOUNTS, newline='') as f:
        reader = csv.reader(f)
        for user, _, password, _ in reader:
            # The first line is a header
            if reader.line_num == 1:
                continue
            if user == username:
                return password


class Account(object):
    def __init__(self, enabled, number, domain, display_name=None):
        self._enabled = enabled
        self._number = number
        self._domain = domain
        self._display_name = display_name

    @property
    def number(self):
        return self._number if self._enabled else ''

    @property
    def display_name(self):
        if self._display_name is not None:
            return self._display_name if self._enabled else ''
        return self.number

    @property
    def enable(self):
        return 1 if self._enabled else 0

    @property
    def label(self):
        return self.number

    @property
    def auth_name(self):
        return self.number

    @property
    def password(self):
        return get_password(self.number) if self._enabled else ''

    @property
    def user_name(self):
        return self.number

    @property
    def hostname(self):
        return self._domain if self._enabled else ''

    @property
    def port(self):
        return 0 if self._enabled else ''

    @property
    def transport(self):
        return 2 if self._enabled else ''


class W52P(object):
    def __init__(self, cfg, prefix, **kwargs):
        self.account = []
        self.cfg = cfg
        self.kwargs = kwargs.copy()
        self.prefix = prefix
        for i in range(0, 5):
            a = Account(True, '%s%01d' % (prefix, i), self.cfg['DOMAIN'])
            self.account.append(a)


    @property
    def base_firmware_url(self):
        if self.cfg['DISABLE_BASE_FIRMWARE_UPGRADE']:
            print('Skipping firmware upgrade (administratively disabled)')
            return '%EMPTY%'
        if self.kwargs['firmware'] == self.cfg['BASE_FIRMWARE_VERSION']:
            print('Skipping firmware upgrade (phone is current)')
            return '%EMPTY%'
        return url_for('static', _external=True, filename=('yealink/w52p/base/%s.rom' % self.cfg['BASE_FIRMWARE_VERSION']))

    @property
    def handset_firmware_url(self):
        if self.cfg['DISABLE_HANDSET_FIRMWARE_UPGRADE']:
            print('Skipping handset firmware upgrade (administratively disabled)')
            return '%EMPTY%'
        return url_for('static', _external=True, filename=('yealink/w52p/handset/%s.rom' % self.cfg['HANDSET_FIRMWARE_VERSION']))

    @property
    def autoprov_server_url(self):
        # Return the URL the client has asked for, but without the
        # filename component.
        url = request.base_url
        return url[:url.rfind('/')]

    @property
    def handset_name(self):
        return [x.display_name for x in self.account]


def load_config():
    try:
        with open(CONFIG) as f:
            cfg = json.loads(f.read())
    except FileNotFoundError:
        cfg = dict()

    if 'DISABLE' not in cfg:
        cfg['DISABLE'] = os.environ.get('DISABLE', False)

    if 'DOMAIN' not in cfg:
        cfg['DOMAIN'] = os.environ['DOMAIN']

    if 'BASE_FIRMWARE_VERSION' not in cfg:
        cfg['BASE_FIRMWARE_VERSION'] = os.environ.get('BASE_FIRMWARE_VERSION', '25.81.0.30')

    if 'HANDSET_FIRMWARE_VERSION' not in cfg:
        cfg['HANDSET_FIRMWARE_VERSION'] = os.environ.get('HANDSET_FIRMWARE_VERSION', '26.73.0.30')

    if 'DISABLE_BASE_FIRMWARE_UPGRADE' not in cfg:
        cfg['DISABLE_BASE_FIRMWARE_UPGRADE'] = os.environ.get('DISABLE_BASE_FIRMWARE_UPGRADE', False)

    if 'DISABLE_HANDSET_FIRMWARE_UPGRADE' not in cfg:
        cfg['DISABLE_HANDSET_FIRMWARE_UPGRADE'] = os.environ.get('DISABLE_HANDSET_FIRMWARE_UPGRADE', False)

    return cfg



def phonebook_lookup(mac):
    try:
        pb = PhoneBook(LEASES)
        return pb.assign(mac)
    except ValueError:
        abort(500)


app = Flask(__name__)
mako = MakoTemplates(app)


@app.route('/<node>/yealink/w52p/<ip>/<mac>/<firmware>/y000000000025.cfg')
def yealink_w52p_common(node, ip, mac, firmware):
    cfg = load_config()
    if cfg['DISABLE']:
        print('Auto-provisioning is administratively disabled')
        abort(404)

    return render_template('yealink/w52p/Common.cfg', name='mako',
        cfg=W52P(cfg, '%s%s' % (NUMBER_PREFIX, phonebook_lookup(mac)), node=node, ip=ip, mac=mac, firmware=firmware))


@app.route('/<node>/yealink/w52p/<ip>/<mac>/<firmware>/<filename>')
def yealink_w52p_mac(node, ip, mac, firmware, filename):
    cfg = load_config()
    if cfg['DISABLE']:
        print('Auto-provisioning is administratively disabled')
        abort(404)

    if filename[12:] != '.cfg':
        abort(404)

    return render_template('yealink/w52p/MAC-Oriented.cfg', name='mako',
        cfg=W52P(cfg, '%s%s' % (NUMBER_PREFIX, phonebook_lookup(mac)), node=node, ip=ip, mac=mac, firmware=firmware))


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)
