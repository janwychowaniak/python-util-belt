"""
Network connectivity checker - Python equivalent of `nc -vz HOST PORT`.

This module provides a simple, dependency-free utility for checking TCP connectivity
to hosts and ports, with support for corporate proxy environments and URL parsing.

Key Features:
    - Direct TCP connectivity checks (like `nc -vz`)
    - Full URL support (extracts host/port automatically)
    - Corporate proxy support via HTTP CONNECT
    - Configurable logging (stdlib, loguru, or custom)
    - Optional environment-based proxy auto-detection
    - Detailed error categorization (timeout, DNS, refused, proxy issues)
    - Zero external dependencies

Basic Usage:
    >>> from ncvz import ncvz
    >>> ncvz('google.com', 80)
    True
    >>> ncvz('internal.service', 5432, timeout=2.0)
    False

URL Usage:
    >>> ncvz('http://127.0.0.1:19000')  # Port extracted from URL
    True
    >>> ncvz('https://api.service.com')  # Port 443 inferred from https scheme
    True
    >>> ncvz('http://example.com:8080', timeout=1.0)
    False

Proxy Usage:
    >>> ncvz('external-api.com', 443, proxy='http://proxy.company.com:8080')
    True
    >>> ncvz_external('api.service.com', 443)  # Uses HTTP_PROXY env var
    True
    >>> ncvz_auto('http://internal.service:5000')  # Auto-detect proxy from env
    True

Custom Logging:
    >>> from loguru import logger
    >>> ncvz('host', 80, logger=logger)
    True

Environment Variables:
    HTTP_PROXY, HTTPS_PROXY - Used by ncvz_auto() and ncvz_external()

Functions:
    ncvz(host, port=None, timeout=3.0, proxy=None, logger=None) -> bool
        Main connectivity checker. Accepts host+port or full URL.
        
    ncvz_auto(host, port=None, timeout=3.0, logger=None) -> bool
        Auto-detect proxy from environment variables. Accepts host+port or URL.
        
    ncvz_external(host, port=None, timeout=3.0, logger=None) -> bool
        Check external host using corporate proxy from environment. Accepts host+port or URL.

Error Types Detected:
    - DNS resolution failures
    - Connection timeouts
    - Connection refused (port closed)
    - Network unreachable
    - Proxy authentication/policy failures (HTTP 403, 407, etc.)
    - Invalid proxy URLs
    - Invalid URL format

Author: Mila 🪄
Version: 1.1
"""

import socket
import time
import logging
from typing import Optional, Any, Union
from urllib.parse import urlparse


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def _parse_host_port(url_or_host: str, port: Optional[int] = None) -> tuple[str, int]:
    """
    Extract host and port from URL or host string.
    
    Args:
        url_or_host: Either a full URL (e.g., 'http://example.com:8080') or hostname
        port: Port number (required if url_or_host is not a URL)
        
    Returns:
        Tuple of (hostname, port)
        
    Raises:
        ValueError: If URL is invalid or port cannot be determined
        
    Examples:
        >>> _parse_host_port('http://example.com:8080')
        ('example.com', 8080)
        >>> _parse_host_port('https://api.service.com')
        ('api.service.com', 443)
        >>> _parse_host_port('example.com', 5432)
        ('example.com', 5432)
    """
    # Check if it looks like a URL (has scheme)
    if '://' in url_or_host:
        parsed = urlparse(url_or_host)
        
        if not parsed.scheme or not parsed.hostname:
            raise ValueError(f"Invalid URL (missing scheme/hostname): {url_or_host}")
        
        # Extract port from URL or use scheme defaults
        if parsed.port is not None:
            final_port = parsed.port
        elif parsed.scheme in ('http', 'ws'):
            final_port = 80
        elif parsed.scheme in ('https', 'wss'):
            final_port = 443
        else:
            # Unknown scheme - require explicit port in URL or raise error
            raise ValueError(f"Cannot determine port for scheme '{parsed.scheme}' in URL: {url_or_host}")
        
        return parsed.hostname, final_port
    else:
        # Not a URL - treat as plain hostname
        if port is None:
            raise ValueError(f"Port required when providing hostname without URL scheme: {url_or_host}")
        return url_or_host, port


def ncvz(
    host: str, 
    port: Optional[int] = None, 
    timeout: float = 3.0,
    proxy: Optional[str] = None,
    logger: Optional[Any] = None
) -> bool:
    """
    Network connectivity check - Python equivalent of `nc -vz HOST PORT`.
    
    Supports both traditional host+port arguments and full URL parsing.
    
    Args:
        host: Target hostname, IP address, or full URL (e.g., 'http://example.com:8080')
        port: Target port number (optional if host is a URL)
        timeout: Connection timeout in seconds
        proxy: Optional proxy URL (e.g., 'http://proxy.company.com:8080')
        logger: Optional logger instance (defaults to stdlib logging)
        
    Returns:
        True if connection successful, False otherwise
        
    Examples:
        # Traditional host + port
        >>> ncvz('google.com', 80)
        True
        >>> ncvz('localhost', 5432, timeout=2.0)
        False
        
        # Full URL (port extracted from URL or scheme)
        >>> ncvz('http://example.com:8080')
        True
        >>> ncvz('https://api.service.com')  # Uses port 443 for https
        True
        >>> ncvz('http://127.0.0.1:19000')
        True
        
        # With proxy
        >>> ncvz('external-api.com', 443, proxy='http://proxy:8080')
        True
        
        # With custom logger (e.g., loguru)
        >>> from loguru import logger
        >>> ncvz('http://host:80', logger=logger)
        True
    """
    # Fallback to stdlib logging if no logger provided
    if logger is None:
        logger = logging.getLogger(__name__)
    
    # Parse host and port (handles both URL and host+port formats)
    try:
        actual_host, actual_port = _parse_host_port(host, port)
    except ValueError as e:
        logger.error(f"ncvz() - Invalid host/URL: {e}")
        return False
    
    start_time = time.time()
    
    try:
        if proxy:
            return _check_via_proxy(actual_host, actual_port, timeout, proxy, start_time, logger)
        else:
            return _check_direct(actual_host, actual_port, timeout, start_time, logger)
            
    except Exception as e:
        elapsed = (time.time() - start_time) * 1000
        logger.error(f"ncvz({actual_host}:{actual_port}) - Unexpected error after {elapsed:.1f}ms: {e}")
        return False


def _check_direct(host: str, port: int, timeout: float, start_time: float, logger: Any) -> bool:
    """Direct socket connection check."""
    try:
        with socket.create_connection((host, port), timeout=timeout) as sock:
            elapsed = (time.time() - start_time) * 1000
            logger.info(f"ncvz({host}:{port}) - Connection succeeded in {elapsed:.1f}ms")
            return True
            
    except socket.timeout:
        logger.warning(f"ncvz({host}:{port}) - Connection timeout after {timeout}s")
        return False
        
    except socket.gaierror as e:
        logger.error(f"ncvz({host}:{port}) - DNS resolution failed: {e}")
        return False
        
    except ConnectionRefusedError:
        elapsed = (time.time() - start_time) * 1000
        logger.warning(f"ncvz({host}:{port}) - Connection refused after {elapsed:.1f}ms")
        return False
        
    except OSError as e:
        elapsed = (time.time() - start_time) * 1000
        logger.error(f"ncvz({host}:{port}) - Network unreachable after {elapsed:.1f}ms: {e}")
        return False


def _check_via_proxy(host: str, port: int, timeout: float, proxy: str, start_time: float, logger: Any) -> bool:
    """Proxy-based connection check using HTTP CONNECT method."""
    try:
        parsed_proxy = urlparse(proxy)
        proxy_host = parsed_proxy.hostname
        proxy_port = parsed_proxy.port or 8080
        
        if not proxy_host:
            logger.error(f"ncvz({host}:{port}) - Invalid proxy URL: {proxy}")
            return False
            
        # Connect to proxy
        with socket.create_connection((proxy_host, proxy_port), timeout=timeout) as proxy_sock:
            # Send HTTP CONNECT request
            connect_request = f"CONNECT {host}:{port} HTTP/1.1\r\nHost: {host}:{port}\r\n\r\n"
            proxy_sock.send(connect_request.encode())
            
            # Read response
            response = proxy_sock.recv(1024).decode()
            
            # Parse HTTP response - check for 2xx status codes
            lines = response.split("\r\n")
            if lines and lines[0]:
                status_line = lines[0]
                # Extract status code (e.g., "HTTP/1.1 200 OK" -> "200")
                parts = status_line.split()
                if len(parts) >= 2:
                    try:
                        status_code = int(parts[1])
                        if 200 <= status_code < 300:  # Any 2xx is success
                            elapsed = (time.time() - start_time) * 1000
                            logger.info(f"ncvz({host}:{port}) - Connection via proxy succeeded in {elapsed:.1f}ms (HTTP {status_code})")
                            return True
                        else:
                            logger.error(f"ncvz({host}:{port}) - Proxy CONNECT failed with HTTP {status_code}")
                            return False
                    except ValueError:
                        logger.error(f"ncvz({host}:{port}) - Invalid proxy response: {status_line}")
                        return False
                else:
                    logger.error(f"ncvz({host}:{port}) - Malformed proxy response: {status_line}")
                    return False
            else:
                logger.error(f"ncvz({host}:{port}) - Empty proxy response")
                return False
                
    except socket.timeout:
        logger.warning(f"ncvz({host}:{port}) - Proxy connection timeout after {timeout}s")
        return False
        
    except socket.gaierror as e:
        logger.error(f"ncvz({host}:{port}) - Proxy DNS resolution failed: {e}")
        return False
        
    except ConnectionRefusedError:
        elapsed = (time.time() - start_time) * 1000
        logger.warning(f"ncvz({host}:{port}) - Proxy connection refused after {elapsed:.1f}ms")
        return False
        
    except Exception as e:
        elapsed = (time.time() - start_time) * 1000
        logger.error(f"ncvz({host}:{port}) - Proxy error after {elapsed:.1f}ms: {e}")
        return False


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

# Convenience function for external tests with environment-based proxy detection
def ncvz_external(
    host: str,
    port: Optional[int] = None,
    timeout: float = 3.0,
    logger: Optional[Any] = None
) -> bool:
    """
    Check external host using proxy from environment.
    
    Args:
        host: Target hostname, IP address, or full URL
        port: Target port number (optional if host is a URL)
        timeout: Connection timeout in seconds
        logger: Optional logger instance
        
    Returns:
        True if connection successful, False otherwise
        
    Examples:
        >>> ncvz_external('api.example.com', 443)
        True
        >>> ncvz_external('https://api.example.com')
        True
    """
    import os
    proxy = os.environ.get("HTTP_PROXY") or os.environ.get("HTTPS_PROXY")
    if not proxy:
        if logger:
            logger.warning(f"No proxy configured for external check: {host}:{port}")
        return False
    return ncvz(host, port, timeout, proxy, logger)


# Convenience function for environment-based proxy detection
def ncvz_auto(
    host: str,
    port: Optional[int] = None,
    timeout: float = 3.0,
    logger: Optional[Any] = None
) -> bool:
    """
    Auto-detect proxy from environment variables (HTTP_PROXY, HTTPS_PROXY).
    
    Args:
        host: Target hostname, IP address, or full URL
        port: Target port number (optional if host is a URL)
        timeout: Connection timeout in seconds
        logger: Optional logger instance
        
    Returns:
        True if connection successful, False otherwise
        
    Examples:
        >>> ncvz_auto('google.com', 80)
        True
        >>> ncvz_auto('http://internal.service:5432')
        True
    """
    import os
    
    proxy = os.environ.get("HTTP_PROXY") or os.environ.get("HTTPS_PROXY")
    return ncvz(host, port, timeout, proxy, logger)
