# gemini_handler/proxy.py
import os
from typing import Dict, Optional

import google.api_core.client_options as client_options
import google.auth.transport.requests
import requests
from google.api_core.rest_transport import RestTransport


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
            
        # Configure requests library session to use proxy
        # This affects any library using requests under the hood
        session = requests.Session()
        session.proxies.update(proxy_settings)
        
        # Replace the default session in the requests module
        requests.Session = lambda: session
    
    @staticmethod
    def get_transport_with_proxy(proxy_settings: Dict[str, str]) -> RestTransport:
        """
        Create a transport with proxy settings.
        
        Args:
            proxy_settings: Dictionary with proxy settings
            
        Returns:
            A transport object configured with proxy settings
        """
        if not proxy_settings:
            return None
            
        # Create a session with proxy settings
        session = requests.Session()
        session.proxies.update(proxy_settings)
        
        # Create transport with the proxy-enabled session
        return RestTransport(session=session)
    
    @staticmethod
    def get_client_options(proxy_settings: Optional[Dict[str, str]] = None) -> client_options.ClientOptions:
        """
        Get client options with proxy settings if provided.
        
        Args:
            proxy_settings: Dictionary with proxy settings
            
        Returns:
            ClientOptions object configured with proxy if needed
        """
        if not proxy_settings:
            return None
            
        # Create custom transport
        transport = ProxyManager.get_transport_with_proxy(proxy_settings)
        
        # Create client options with the transport
        options = client_options.ClientOptions(
            api_endpoint="generativelanguage.googleapis.com",
            rest_transport=transport
        )
        
        return options
