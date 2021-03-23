# Auto-provisioning Tool for Yealink W52P Phones

This tool implements an auto-provisioning server for Yealink W52P IP
DECT phones. The tool includes the latest firmware blobs and a
database of user-password combinations for the PHOENIX network. The
tool serves both configuration and firmware images to the phones.

The tool consists of two programs, a multicast agent that must be
running in the same layer two network as the phone, and a HTTP-based
provisioning server. Both programs are implemented in Python. The HTTP
provisioning server is based on the Flask framework and Mako
templating engine.

When booting, the Yealink W52P IP DECT phone searches the LAN for an
auto-provisioning server using UPnP multicast. The auto-provisioning
server responds to the multicast request and redirects to the phone to
a HTTP-based auto-provisioning server. The HTTP server then servers
the firmware blob and a configuration file to the phone.

Note: Please remember to configure the domain to be used by the
provisioning tool using the DOMAIN environment variable. The value
specified via the environment variable will be used in the hostname
portion of any SIP URIs.

Written by Jan Janak (janakj@cs.columbia.edu)
