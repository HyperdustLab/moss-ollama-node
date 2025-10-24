#!/usr/bin/env python3
import logging
import os
import socket
import threading
import signal
import inspect
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

from flask import Flask, jsonify
from nacos import NacosClient
from eth_utils import is_address

# -----------------------------
# Logging
# -----------------------------
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s | %(levelname)s | %(threadName)s | %(message)s",
)

app = Flask(__name__)

# -----------------------------
# Configuration (ENV)
# -----------------------------
# Explicitly use HTTP protocol; change port if 8848 is needed
NACOS_SERVER = os.getenv("NACOS_SERVER", "http://nacos.hyperagi.network:80")
NACOS_HTTP_TIMEOUT = float(os.getenv("NACOS_HTTP_TIMEOUT", "5.0"))

PUBLIC_IP = os.getenv("PUBLIC_IP", "")
PORT = int(os.getenv("PORT", 11434))  # Unified: both registration and Flask use it

SERVICE_NAME = os.getenv("SERVICE_NAME", "")
WALLET_ADDRESS = os.getenv("WALLET_ADDRESS", "")
NODE = os.getenv("NODE", PUBLIC_IP)

NACOS_USERNAME = os.getenv("NACOS_USERNAME", "")
NACOS_PASSWORD = os.getenv("NACOS_PASSWORD", "")

# Retry / heartbeat
MAX_RECONNECT_DELAY = int(os.getenv("MAX_RECONNECT_DELAY", 300))
INITIAL_RECONNECT_DELAY = int(os.getenv("INITIAL_RECONNECT_DELAY", 5))
HEARTBEAT_INTERVAL = int(os.getenv("HEARTBEAT_INTERVAL", 5))

# Optional: group/cluster (if server has routing policy)
NACOS_GROUP = os.getenv("NACOS_GROUP", "DEFAULT_GROUP")
NACOS_CLUSTER = os.getenv("NACOS_CLUSTER", "")

# -----------------------------
# Global state
# -----------------------------
is_connected = False
reconnect_lock = threading.Lock()
stop_event = threading.Event()
client = None  # type: NacosClient | None

# -----------------------------
# Utilities: DNS & TCP checks
# -----------------------------
def _parse_host_port(server: str) -> tuple[str, int]:
    """
    Supports three formats:
      - http://host:port
      - https://host:port   (although this script defaults to http, parsing is still compatible)
      - host:port           (will be completed as http://host:port)
    """
    if "://" not in server:
        parsed = urlparse(f"http://{server}")
    else:
        parsed = urlparse(server)

    host = parsed.hostname or server
    port = parsed.port or (80 if parsed.scheme in ("", "http") else 443)
    return host, port

def check_dns_resolvable(host: str) -> bool:
    try:
        infos = socket.getaddrinfo(host, None, proto=socket.IPPROTO_TCP)
        addrs = sorted({x[4][0] for x in infos})
        logging.info(f"DNS OK: {host} -> {addrs}")
        return True
    except Exception as e:
        logging.error(f"DNS FAIL: {host} not resolvable: {e}")
        return False

def check_tcp_connect(host: str, port: int, timeout=3) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            logging.info(f"TCP OK: {host}:{port} reachable")
            return True
    except Exception as e:
        logging.error(f"TCP FAIL: {host}:{port} not reachable: {e}")
        return False

def check_port_available(port: int, host="0.0.0.0") -> bool:
    """Check if local listening port is available (not occupied)"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind((host, port))
        s.close()
        logging.info(f"PORT OK: {host}:{port} available for binding")
        return True
    except Exception as e:
        logging.error(f"PORT FAIL: {host}:{port} cannot bind: {e}")
        return False

def _build_base_url(server: str) -> str:
    if "://" not in server:
        return f"http://{server}"
    return server

def _probe_nacos_http(server: str):
    """
    Lightweight HTTP probe:
    - First probe /nacos/v1/console/health
    - If 404, try /v1/console/health (some gateways don't have /nacos prefix)
    Only log output, don't interrupt startup.
    """
    base = _build_base_url(server).rstrip("/")
    for path in ("/nacos/v1/console/health", "/v1/console/health"):
        url = f"{base}{path}"
        try:
            req = Request(url, method="GET")
            with urlopen(req, timeout=NACOS_HTTP_TIMEOUT) as resp:
                body = resp.read(128).decode("utf-8", errors="ignore")
                logging.info(f"HTTP PROBE OK {url} status={resp.status} body={body}")
                return
        except HTTPError as e:
            logging.warning(f"HTTP PROBE {url} HTTP {e.code}")
        except URLError as e:
            logging.warning(f"HTTP PROBE {url} error={e.reason}")
        except Exception as e:
            logging.warning(f"HTTP PROBE {url} error={e}")
    logging.warning("HTTP PROBE failed on all known health endpoints")

# -----------------------------
# Validations
# -----------------------------
def validate_env_or_die():
    if not WALLET_ADDRESS or not is_address(WALLET_ADDRESS):
        raise ValueError("Invalid or empty WALLET_ADDRESS")
    if not PUBLIC_IP:
        raise ValueError("PUBLIC_IP is required")
    if not SERVICE_NAME:
        raise ValueError("SERVICE_NAME is required")

def preflight_or_die():
    """Startup preflight check: DNS, TCP connectivity, port available + HTTP probe"""
    first = NACOS_SERVER.split(",")[0].strip()
    host, port = _parse_host_port(first)

    ok = True
    ok &= check_dns_resolvable(host)
    ok &= check_tcp_connect(host, port)
    ok &= check_port_available(PORT)

    logging.info(f"user server address  {NACOS_SERVER}")
    _probe_nacos_http(first)

    if not ok:
        raise RuntimeError("Preflight checks failed. See logs above.")

# -----------------------------
# Nacos client helpers (+ ctor compatibility)
# -----------------------------
def _construct_nacos_client(servers: str) -> NacosClient:
    """
    Some nacos-sdk-python versions don't support default_timeout parameter, 
    here we check the signature before passing it.
    """
    kwargs = {
        "server_addresses": servers,
        "namespace": "",
        "username": NACOS_USERNAME,
        "password": NACOS_PASSWORD,
    }
    sig = inspect.signature(NacosClient.__init__)
    if "default_timeout" in sig.parameters:
        kwargs["default_timeout"] = NACOS_HTTP_TIMEOUT
    return NacosClient(**kwargs)

def create_nacos_client() -> NacosClient:
    logging.info(f"user server address  {NACOS_SERVER}")
    # Support multiple addresses separated by commas; ensure each has protocol
    servers = ",".join(_build_base_url(s.strip()) for s in NACOS_SERVER.split(",") if s.strip())
    # Print init logs similar to SDK to help align with your existing log style
    logging.info("[client-init] endpoint:None, tenant:")
    return _construct_nacos_client(servers)

# ---- Compatibility layer: automatically adapt parameter names for different SDK versions -----------------
def _call_with_supported_kwargs(func, *args, **kwargs):
    """
    Read func signature, remove unsupported keys from kwargs;
    Also automatically map 'enabled' to 'enable' (if exists).
    """
    sig = inspect.signature(func)
    params = sig.parameters

    # Compatibility: enabled -> enable
    if "enabled" in kwargs and "enable" in params:
        kwargs["enable"] = kwargs.pop("enabled")
    elif "enabled" in kwargs and "enable" not in params:
        kwargs.pop("enabled")

    # If function doesn't have **kwargs, discard unsupported keys
    accepts_varkw = any(p.kind == p.VAR_KEYWORD for p in params.values())
    if not accepts_varkw:
        kwargs = {k: v for k, v in kwargs.items() if k in params}

    return func(*args, **kwargs)

def add_instance_compat(client, **kwargs):
    return _call_with_supported_kwargs(client.add_naming_instance, **kwargs)

def send_heartbeat_compat(client, **kwargs):
    return _call_with_supported_kwargs(client.send_heartbeat, **kwargs)

def remove_instance_compat(client, **kwargs):
    return _call_with_supported_kwargs(client.remove_naming_instance, **kwargs)
# -----------------------------------------------------------

def register_service() -> None:
    """Try immediate registration (may throw error). Set is_connected=True on success"""
    global is_connected
    metadata = {"walletAddress": WALLET_ADDRESS, "node": NODE}

    # Print pre-logs similar to SDK for easier troubleshooting
    logging.info(f"[add-naming-instance] ip:{PUBLIC_IP}, port:{PORT}, service_name:{SERVICE_NAME}, namespace:")

    add_instance_compat(
        client,
        service_name=SERVICE_NAME,
        ip=PUBLIC_IP,
        port=PORT,
        group_name=NACOS_GROUP,
        cluster_name=(NACOS_CLUSTER or None),
        metadata=metadata,
        ephemeral=True,
        enabled=True,   # Compatibility layer will automatically map/remove
        healthy=True,
    )
    is_connected = True
    logging.info(
        f"Registered: service={SERVICE_NAME} ip={PUBLIC_IP} port={PORT} "
        f"group={NACOS_GROUP} cluster={NACOS_CLUSTER or '-'} meta={metadata}"
    )

def attempt_reconnect_once() -> bool:
    """Reconnect/first connect once with lock; return True on success"""
    global client, is_connected
    with reconnect_lock:
        if stop_event.is_set():
            return False
        try:
            logging.info(f"user server address  {NACOS_SERVER}")
            client = create_nacos_client()
            logging.info("[client-init] endpoint:None, tenant:")
            register_service()
            return True
        except Exception as e:
            is_connected = False
            logging.error(f"Reconnect/register failed: {e}")
            return False

def backoff_delay(attempt: int) -> int:
    return min(INITIAL_RECONNECT_DELAY * (2 ** max(0, attempt - 1)), MAX_RECONNECT_DELAY)

def reconnect_worker():
    """Keep trying to connect until successful; wait for disconnection after connecting"""
    attempt = 1
    while not stop_event.is_set():
        if not is_connected:
            if attempt_reconnect_once():
                logging.info("Connection established; normal operation resumes")
                attempt = 1
            else:
                delay = backoff_delay(attempt)
                logging.warning(f"Reconnect attempt #{attempt} failed. Retry in {delay}s ...")
                attempt += 1
                stop_event.wait(delay)
        else:
            stop_event.wait(HEARTBEAT_INTERVAL)

def heartbeat_worker():
    """Heartbeat maintenance, consider disconnected after 3 consecutive failures"""
    global is_connected
    fail = 0
    while not stop_event.is_set():
        if is_connected:
            try:
                send_heartbeat_compat(
                    client,
                    service_name=SERVICE_NAME,
                    ip=PUBLIC_IP,
                    port=PORT,
                    group_name=NACOS_GROUP,
                    cluster_name=(NACOS_CLUSTER or None),
                    metadata={"walletAddress": WALLET_ADDRESS, "node": NODE},
                    ephemeral=True,
                )
                logging.info("Heartbeat OK")
                fail = 0
            except Exception as e:
                fail += 1
                logging.error(f"Heartbeat FAIL ({fail}): {e}")
                if fail >= 3:
                    is_connected = False
                    logging.warning("Marked disconnected due to repeated heartbeat failures")
                    fail = 0
        stop_event.wait(HEARTBEAT_INTERVAL)

def graceful_shutdown(*_args):
    """SIGTERM/SIGINT graceful shutdown"""
    logging.info("Shutting down ...")
    stop_event.set()
    # Regardless of is_connected status, try deregistration once
    try:
        if client:
            remove_instance_compat(
                client,
                service_name=SERVICE_NAME,
                ip=PUBLIC_IP,
                port=PORT,
                group_name=NACOS_GROUP,
                cluster_name=(NACOS_CLUSTER or None),
                ephemeral=True,
            )
            logging.info("Deregistered from Nacos")
    except Exception as e:
        logging.error(f"Deregister failed: {e}")

# -----------------------------
# Flask routes
# -----------------------------
@app.get("/health")
def health():
    return jsonify(
        {
            "service": SERVICE_NAME,
            "status": "UP" if is_connected else "DEGRADED",
            "public_ip": PUBLIC_IP,
            "port": PORT,
            "node": NODE,
            "nacos_server": NACOS_SERVER,
            "group": NACOS_GROUP,
            "cluster": NACOS_CLUSTER or "",
        }
    ), (200 if is_connected else 206)

@app.get("/")
def root():
    return "OK", 200

# -----------------------------
# Main
# -----------------------------
def main():
    validate_env_or_die()
    preflight_or_die()

    # Register signal handlers (Docker/K8s graceful shutdown)
    signal.signal(signal.SIGINT, graceful_shutdown)
    signal.signal(signal.SIGTERM, graceful_shutdown)

    # Start background daemon threads first (initial registration is also handled by it)
    threading.Thread(target=reconnect_worker, name="reconnector", daemon=True).start()
    threading.Thread(target=heartbeat_worker, name="heartbeat", daemon=True).start()

    # Optional: try immediate registration once (don't exit on failure, let background thread continue)
    try:
        global client
        client = create_nacos_client()
        logging.info("[client-init] endpoint:None, tenant:")
        register_service()
    except Exception as e:
        logging.warning(f"Initial register failed; background will retry. reason={e}")

    # Flask and registration port unified (must be consistent)
    app.run(host="0.0.0.0", port=PORT)

if __name__ == "__main__":
    try:
        main()
    finally:
        graceful_shutdown()
