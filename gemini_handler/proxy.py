# gemini_handler/proxy.py
import os
from typing import Dict, Optional

import requests


class ProxyManager:
    """Manages proxy configuration for API requests."""
    
    @staticmethod
    def configure_proxy(proxy_settings: Optional[Dict[str, str]] = None) -> None:
        """
        Configure proxy settings for requests library.
        This affects all subsequent HTTP requests made with the requests library.
        
        Args:
            proxy_settings: Dictionary with proxy settings (e.g., {'http': 'http://proxy:port', 'https': 'https://proxy:port'})
        """
        if not proxy_settings:
            return
            
        # Set environment variables for libraries that use them directly
        if 'http' in proxy_settings:
            os.environ['HTTP_PROXY'] = proxy_settings['http']
        if 'https' in proxy_settings:
            os.environ['HTTPS_PROXY'] = proxy_settings['https']
    
    @staticmethod
    def get_client_options(proxy_settings: Optional[Dict[str, str]] = None):
        """
        Since we're using environment variables for proxy configuration,
        we don't need specific client options. This is maintained for
        compatibility with the existing code structure.
        
        Returns:
            None since we're using environment variables instead
        """
        return None

    @staticmethod
    def format_proxy_url(host, port, username=None, password=None, protocol="http"):
        """Format a proxy URL with optional authentication."""
        auth_part = f"{username}:{password}@" if username and password else ""
        return f"{protocol}://{auth_part}{host}:{port}"
        
    @staticmethod
    def configure_proxy_with_auth(host, port, username=None, password=None):
        """Configure proxy with separate authentication parameters."""
        proxy_settings = {
            'http': ProxyManager.format_proxy_url(host, port, username, password, "http"),
            'https': ProxyManager.format_proxy_url(host, port, username, password, "https")
        }
        ProxyManager.configure_proxy(proxy_settings)
        return proxy_settings