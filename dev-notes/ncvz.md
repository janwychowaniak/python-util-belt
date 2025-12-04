```py
from ncvz import ncvz, ncvz_external, ncvz_auto

# Proxy addresses for tests (if connectivity tests via proxy required, apart from direct)
PROXY_OK = "http://IP_1:3128/"       # something healthy
PROXY_MALF = "IP_1:3128"             # something malformed (test for: malformed proxy URL)
PROXY_DEAD = "http://IP_2:3128/"     # something not responding (test for: timeout)
PROXY_LH = "http://127.0.0.1:3128/"  # something deliberately refusing connections (port assumed unbound)

# Destinations for tests
DEST_INTRA = "host.intranet"     # Two separate target handlers can be useful...
DEST_WORLD = "stat.ripe.net"     # ... if connectivity is tested inside and out of a proxy-guarded corporate network
DEST_BADDNS = "no.such.domain"   # For testing DNS problems
DEST_LOCALH = "127.0.0.1"

# Port numbers for tests
PORT_OK = 443  # HTTPS, most typically safe
PORT_BAD = 0   # Something invalid surely
```

```py
# Logging: not configured (fallback to stdlib) --------------------------------

## Check: no proxy (direct/intranet)

ncvz(DEST_INTRA, PORT_OK)    # ✔
ncvz(DEST_INTRA, PORT_BAD)   # ✘ (Connection timeout)

ncvz(DEST_WORLD, PORT_OK)    # ✘ (Connection timeout)
ncvz(DEST_WORLD, PORT_BAD)   # ✘ (Connection timeout)

ncvz(DEST_BADDNS, PORT_OK)   # ✘ (DNS resolution failed)
ncvz(DEST_BADDNS, PORT_BAD)  # ✘ (DNS resolution failed)

ncvz(DEST_LOCALH, PORT_BAD)  # ✘ (Connection refused)

## Check: via proxy (manual)

ncvz(DEST_WORLD, PORT_OK, proxy=PROXY_OK)     # ✔
ncvz(DEST_WORLD, PORT_BAD, proxy=PROXY_OK)    # ✔  (??)

ncvz(DEST_INTRA, PORT_OK, proxy=PROXY_OK)     # ✘ (Proxy CONNECT failed with HTTP 403)
ncvz(DEST_INTRA, PORT_BAD, proxy=PROXY_OK)    # ✘ (Proxy CONNECT failed with HTTP 403)

ncvz(DEST_BADDNS, PORT_OK, proxy=PROXY_OK)    # ✘ (Proxy CONNECT failed with HTTP 403)
ncvz(DEST_BADDNS, PORT_BAD, proxy=PROXY_OK)   # ✘ (Proxy CONNECT failed with HTTP 403)

ncvz(DEST_LOCALH, PORT_OK, proxy=PROXY_OK)    # ✘ (Proxy CONNECT failed with HTTP 403)
ncvz(DEST_LOCALH, PORT_BAD, proxy=PROXY_OK)   # ✘ (Proxy CONNECT failed with HTTP 403)

ncvz(DEST_WORLD, PORT_OK, proxy=PROXY_MALF)   # ✘ (Invalid proxy URL)
ncvz(DEST_WORLD, PORT_OK, proxy=PROXY_DEAD)   # ✘ (Proxy connection timeout)
ncvz(DEST_WORLD, PORT_OK, proxy=PROXY_LH)     # ✘ (Proxy connection refused)

## Check: via proxy (env)

ncvz_external(DEST_WORLD, PORT_OK)   # ✔
ncvz_external(DEST_WORLD, PORT_BAD)  # ✔

ncvz_external(DEST_INTRA, PORT_OK)   # ✘ (Proxy CONNECT failed with HTTP 403)
ncvz_external(DEST_INTRA, PORT_BAD)  # ✘ (Proxy CONNECT failed with HTTP 403)

ncvz_external(DEST_BADDNS, PORT_OK)  # ✘ (Proxy CONNECT failed with HTTP 403)
ncvz_external(DEST_BADDNS, PORT_BAD) # ✘ (Proxy CONNECT failed with HTTP 403)

ncvz_external(DEST_LOCALH, PORT_OK)  # ✘ (Proxy CONNECT failed with HTTP 403)
ncvz_external(DEST_LOCALH, PORT_BAD) # ✘ (Proxy CONNECT failed with HTTP 403)

## Check: proxy auto (env)

ncvz_auto(DEST_WORLD, PORT_OK)   # ✔
ncvz_auto(DEST_WORLD, PORT_BAD)  # ✔

ncvz_auto(DEST_INTRA, PORT_OK)   # ✘ (Proxy CONNECT failed with HTTP 403)
ncvz_auto(DEST_INTRA, PORT_BAD)  # ✘ (Proxy CONNECT failed with HTTP 403)

ncvz_auto(DEST_BADDNS, PORT_OK)  # ✘ (Proxy CONNECT failed with HTTP 403)
ncvz_auto(DEST_BADDNS, PORT_BAD) # ✘ (Proxy CONNECT failed with HTTP 403)

ncvz_auto(DEST_LOCALH, PORT_OK)  # ✘ (Proxy CONNECT failed with HTTP 403)
ncvz_auto(DEST_LOCALH, PORT_BAD) # ✘ (Proxy CONNECT failed with HTTP 403)

# Logging: loguru -------------------------------------------------------------

from loguru import logger

## Check: no proxy (direct/intranet)

ncvz(DEST_INTRA, PORT_OK, logger=logger)    # ✔
ncvz(DEST_INTRA, PORT_BAD, logger=logger)   # ✘ (Connection timeout)

ncvz(DEST_WORLD, PORT_OK, logger=logger)    # ✘ (Connection timeout)
ncvz(DEST_WORLD, PORT_BAD, logger=logger)   # ✘ (Connection timeout)

ncvz(DEST_BADDNS, PORT_OK, logger=logger)   # ✘ (DNS resolution failed)
ncvz(DEST_BADDNS, PORT_BAD, logger=logger)  # ✘ (DNS resolution failed)

ncvz(DEST_LOCALH, PORT_BAD, logger=logger)  # ✘ (Connection refused)

# Logging: manual stdlib ------------------------------------------------------

import logging
logger = logging.getLogger('network_checks')

## Check: no proxy (direct/intranet)

ncvz(DEST_INTRA, PORT_OK, logger=logger)    # ✔
ncvz(DEST_INTRA, PORT_BAD, logger=logger)   # ✘ (Connection timeout)

ncvz(DEST_WORLD, PORT_OK, logger=logger)    # ✘ (Connection timeout)
ncvz(DEST_WORLD, PORT_BAD, logger=logger)   # ✘ (Connection timeout)

ncvz(DEST_BADDNS, PORT_OK, logger=logger)   # ✘ (DNS resolution failed)
ncvz(DEST_BADDNS, PORT_BAD, logger=logger)  # ✘ (DNS resolution failed)

ncvz(DEST_LOCALH, PORT_BAD, logger=logger)  # ✘ (Connection refused)

# Logging: custom -------------------------------------------------------------

class SilentLogger:
    def info(self, msg): pass
    def warning(self, msg): pass
    def error(self, msg): pass

logger=SilentLogger()

## Check: no proxy (direct/intranet)

ncvz(DEST_INTRA, PORT_OK, logger=logger)    # ✔
ncvz(DEST_INTRA, PORT_BAD, logger=logger)   # ✘ (Connection timeout)

ncvz(DEST_WORLD, PORT_OK, logger=logger)    # ✘ (Connection timeout)
ncvz(DEST_WORLD, PORT_BAD, logger=logger)   # ✘ (Connection timeout)

ncvz(DEST_BADDNS, PORT_OK, logger=logger)   # ✘ (DNS resolution failed)
ncvz(DEST_BADDNS, PORT_BAD, logger=logger)  # ✘ (DNS resolution failed)

ncvz(DEST_LOCALH, PORT_BAD, logger=logger)  # ✘ (Connection refused)
```
