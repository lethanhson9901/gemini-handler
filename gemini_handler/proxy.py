# gemini_handler/proxy.py
import os
import threading  # Import threading
import time
from typing import Any, Dict, List, Optional, Union

# Import the auto proxy functionality
try:
    from swiftshadow.classes import Proxy, ProxyInterface
    SWIFTSHADOW_AVAILABLE = True
except ImportError:
    SWIFTSHADOW_AVAILABLE = False
    print("SwiftShadow library not available. Auto proxy features will be disabled.")
    # Create dummy Proxy class for type hints
    class Proxy:
        def as_string(self) -> str:
            return ""


class ProxyManager:
    """Manages proxy configuration for API requests."""

    # Class variables for tracking proxies
    _auto_proxy_interface = None
    _current_static_proxy = None
    _current_auto_proxy = None
    _proxy_history = []
    _max_history = 10
    _auto_update = False
    _auto_rotate = False
    _update_interval = 15
    _update_thread = None
    _initialized = False
    _current_proxy_index = -1 # Start at -1 so first call goes to 0
    _lock = threading.RLock() # Add a lock for thread safety on index

    @classmethod
    def configure_proxy(cls, proxy_settings: Optional[Dict[str, Any]] = None) -> None:
        """
        Configure proxy settings. Initializes auto-proxy if specified.

        Args:
            proxy_settings: Dictionary with proxy settings
                          - Standard format: {'http': 'http://proxy:port', 'https': 'https://proxy:port'}
                          - Can also include 'auto_proxy' key with auto proxy settings
        """
        with cls._lock: # Ensure thread safety during configuration
            cls._current_static_proxy = None # Reset static proxy
            cls._current_auto_proxy = None # Reset auto proxy state on reconfigure
            cls._initialized = False # Reset initialized state
            cls._current_proxy_index = -1 # Reset index

            if not proxy_settings:
                # Clear environment variables if no settings provided
                os.environ.pop('HTTP_PROXY', None)
                os.environ.pop('HTTPS_PROXY', None)
                print("Proxy settings cleared.")
                return

            # Check for auto proxy settings
            if 'auto_proxy' in proxy_settings and SWIFTSHADOW_AVAILABLE:
                auto_config = proxy_settings['auto_proxy']
                cls._auto_update = auto_config.get('auto_update', False)
                cls._auto_rotate = auto_config.get('auto_rotate', True)
                cls._update_interval = auto_config.get('update_interval', 15)

                # Initialize the auto proxy system
                try:
                    # Create the ProxyInterface if it doesn't exist
                    if cls._auto_proxy_interface is None:
                         cls._auto_proxy_interface = ProxyInterface(autoUpdate=False, autoRotate=False)

                    # Initial proxy update
                    print("Attempting initial proxy update...")
                    cls._auto_proxy_interface.update()
                    print(f"Initial proxy update successful, got {len(cls._auto_proxy_interface.proxies)} proxies")

                    # Start background update thread if auto_update is enabled and thread isn't running
                    if cls._auto_update and (cls._update_thread is None or not cls._update_thread.is_alive()):
                        cls._start_update_thread()

                    cls._initialized = True
                    print("Auto Proxy Initialized.")

                    # Apply an initial proxy if auto_rotate is enabled
                    if cls._auto_rotate:
                        print("Applying initial proxy due to auto_rotate=True...")
                        # Don't set environment here, middleware will handle it on first request
                        # cls.apply_next_proxy(set_environment=True)
                        cls.get_next_proxy() # Call once to prime the first proxy selection

                except Exception as e:
                    print(f"Failed to initialize auto proxy: {e}. Falling back to static proxy if configured.")
                    # Fall back to regular proxy settings if auto proxy fails
                    cls._apply_static_proxy(proxy_settings)
                    cls._initialized = True # Mark as initialized even for static proxy fallback
            else:
                # Regular proxy configuration (without auto proxy)
                print("Configuring static proxy.")
                cls._apply_static_proxy(proxy_settings)
                cls._initialized = True # Mark as initialized even for static proxy

    @classmethod
    def _apply_static_proxy(cls, proxy_settings: Dict[str, Any], set_environment: bool = True) -> None:
        """Apply static proxy settings to environment and internal state."""
        http_proxy = proxy_settings.get('http')
        https_proxy = proxy_settings.get('https')

        if set_environment:
            if http_proxy:
                os.environ['HTTP_PROXY'] = http_proxy
                print(f"Set HTTP_PROXY environment variable.")
            else:
                os.environ.pop('HTTP_PROXY', None)

            if https_proxy:
                os.environ['HTTPS_PROXY'] = https_proxy
                print(f"Set HTTPS_PROXY environment variable.")
            else:
                os.environ.pop('HTTPS_PROXY', None)

        # Track the current static proxy
        cls._current_static_proxy = {
            'http': http_proxy,
            'https': https_proxy,
            'timestamp': time.time(),
            'proxy_string': cls._extract_host_port(https_proxy or http_proxy or ''),
            'source': 'static'
        }
        cls._add_to_history(cls._current_static_proxy)

    @classmethod
    def _start_update_thread(cls) -> None:
        """Start a background thread for periodic proxy updates."""
        # Use the existing lock for thread safety
        # import threading # Already imported

        if cls._update_thread is not None and cls._update_thread.is_alive():
            print("Proxy update thread already running.")
            return

        def update_proxies():
            while True:
                try:
                    # Check conditions within the loop
                    with cls._lock:
                         should_run = cls._auto_update and cls._initialized and cls._auto_proxy_interface is not None

                    if not should_run:
                         print("Auto update disabled or not initialized. Stopping update thread.")
                         break

                    time.sleep(cls._update_interval)

                    with cls._lock:
                        # Re-check conditions before update, in case config changed
                        if cls._auto_proxy_interface and cls._auto_update and cls._initialized:
                            print(f"Updating proxies... (interval: {cls._update_interval}s)")
                            try:
                                cls._auto_proxy_interface.update()
                                print(f"Proxy update successful, now have {len(cls._auto_proxy_interface.proxies)} proxies")
                                # Reset index if list shrinks beyond current index
                                if cls._current_proxy_index >= len(cls._auto_proxy_interface.proxies):
                                    cls._current_proxy_index = -1
                            except Exception as update_e:
                                print(f"Error during proxy update: {update_e}")
                        else:
                             # Condition changed while sleeping, break
                             print("Proxy update conditions changed. Stopping update thread.")
                             break
                except Exception as e:
                    print(f"Error in proxy update loop: {e}")
                    time.sleep(5)  # Back off on error

        cls._update_thread = threading.Thread(target=update_proxies, daemon=True)
        cls._update_thread.start()
        print("Started proxy update background thread.")

    @classmethod
    def _add_to_history(cls, proxy_info: Dict[str, Any]) -> None:
        """Add a proxy to the history list."""
        if proxy_info:
            cls._proxy_history.append(proxy_info)
            # Keep history limited to max size
            if len(cls._proxy_history) > cls._max_history:
                cls._proxy_history.pop(0)

    @classmethod
    def get_next_proxy(cls) -> Optional[Dict[str, str]]:
        """
        Get the next proxy dictionary based on the configured strategy (auto or static).
        Updates the internal state (_current_auto_proxy or _current_static_proxy).

        Returns:
            Dictionary with http/https settings or None
        """
        with cls._lock: # Ensure thread safety for index and list access
            # --- Auto Proxy Logic ---
            if SWIFTSHADOW_AVAILABLE and cls._initialized and cls._auto_proxy_interface and cls._auto_rotate:
                proxies = cls._auto_proxy_interface.proxies
                if not proxies:
                    print("Warning: Auto proxy enabled, but no proxies available.")
                    # Optional: Attempt an update if list is empty?
                    # try:
                    #     cls._auto_proxy_interface.update()
                    #     proxies = cls._auto_proxy_interface.proxies
                    #     if not proxies: print("Still no proxies after update attempt.")
                    # except Exception as update_err: print(f"Error updating empty proxy list: {update_err}")
                    cls._current_auto_proxy = None # No proxy to set
                    return None

                # Rotate index
                cls._current_proxy_index = (cls._current_proxy_index + 1) % len(proxies)
                selected_proxy_obj = proxies[cls._current_proxy_index]

                if selected_proxy_obj:
                    proxy_str = selected_proxy_obj.as_string()
                    # Assume http for both, common practice
                    http_url = f"http://{proxy_str}"
                    https_url = f"http://{proxy_str}" # HTTPS traffic often goes via HTTP proxy

                    proxy_info = {
                        'proxy_string': cls._extract_host_port(proxy_str), # Store cleaned host:port
                        'timestamp': time.time(),
                        'http': http_url,
                        'https': https_url,
                        'source': 'auto'
                    }
                    cls._current_auto_proxy = proxy_info
                    cls._add_to_history(proxy_info)
                    # print(f"Selected auto proxy index {cls._current_proxy_index}: {proxy_info['proxy_string']}") # Debug log
                    return {'http': http_url, 'https': https_url}
                else:
                    print(f"Warning: Got None proxy object at index {cls._current_proxy_index}")
                    cls._current_auto_proxy = None
                    return None

            # --- Static Proxy Logic ---
            elif cls._current_static_proxy:
                # Static proxy doesn't rotate, just return its settings
                # The state (_current_static_proxy) was set during configure_proxy
                # print("Returning static proxy settings.") # Debug log
                return {
                    'http': cls._current_static_proxy.get('http'),
                    'https': cls._current_static_proxy.get('https')
                }

            # --- No Proxy ---
            else:
                # print("No proxy configured or available.") # Debug log
                cls._current_auto_proxy = None # Ensure auto is cleared
                return None

    @classmethod
    def apply_next_proxy(cls, set_environment: bool = True) -> Optional[Dict[str, str]]:
        """
        Gets the next proxy and optionally applies it to environment variables.
        This updates the internal current proxy state.

        Args:
            set_environment: Whether to set os.environ variables.

        Returns:
            The proxy dictionary that was applied (or attempted), or None.
        """
        # get_next_proxy now handles selecting the proxy and updating internal state
        proxy_dict = cls.get_next_proxy()

        if set_environment:
            if proxy_dict:
                http_proxy = proxy_dict.get('http')
                https_proxy = proxy_dict.get('https')

                if http_proxy:
                    os.environ['HTTP_PROXY'] = http_proxy
                else:
                    os.environ.pop('HTTP_PROXY', None)

                if https_proxy:
                    os.environ['HTTPS_PROXY'] = https_proxy
                else:
                    os.environ.pop('HTTPS_PROXY', None)

                # Log based on the actual current proxy state after get_next_proxy
                current_proxy_info = cls.get_current_proxy()
                current_proxy_str = current_proxy_info.get('proxy_string', 'N/A') if current_proxy_info else 'None'
                print(f"Applied proxy to environment: {current_proxy_str}")
            else:
                # Explicitly clear environment if no proxy was selected
                os.environ.pop('HTTP_PROXY', None)
                os.environ.pop('HTTPS_PROXY', None)
                print("Cleared proxy environment variables (no proxy selected).")


        return proxy_dict # Return the dict whether applied to env or not

    @classmethod
    def get_current_proxy(cls) -> Optional[Dict[str, Any]]:
        """
        Get information about the currently active proxy (auto or static).
        Reflects the state set by the last call to get_next_proxy/apply_next_proxy.

        Returns:
            Dictionary with current proxy info or None
        """
        with cls._lock:
            # Prefer auto proxy info if it's active and rotating
            if cls._current_auto_proxy and cls._auto_rotate:
                return cls._current_auto_proxy

            # Fall back to static proxy info
            return cls._current_static_proxy

    @classmethod
    def get_proxy_history(cls) -> List[Dict[str, Any]]:
        """
        Get history of recently used proxies.

        Returns:
            List of proxy information dictionaries
        """
        with cls._lock:
            return cls._proxy_history.copy()

    @classmethod
    def get_proxy_stats(cls) -> Dict[str, Any]:
        """
        Get proxy statistics.

        Returns:
            Dictionary with proxy stats
        """
        with cls._lock:
            is_auto = SWIFTSHADOW_AVAILABLE and cls._initialized and cls._auto_proxy_interface is not None
            current_p = cls.get_current_proxy() # Use the method to get current

            stats = {
                'initialized': cls._initialized,
                'using_auto_proxy': is_auto and (cls._auto_rotate or cls._auto_update),
                'auto_update_enabled': is_auto and cls._auto_update,
                'auto_rotate_enabled': is_auto and cls._auto_rotate,
                'update_interval': cls._update_interval if is_auto else None,
                'proxy_count': len(cls._auto_proxy_interface.proxies) if is_auto and cls._auto_proxy_interface.proxies else (1 if cls._current_static_proxy else 0),
                'current_proxy_index': cls._current_proxy_index if is_auto and cls._auto_rotate else None, # Add index info
                'current_proxy': current_p,
                'proxy_history': cls._proxy_history.copy(), # Return a copy
            }
            return stats

    @classmethod
    async def async_update(cls) -> bool:
        """
        Update proxies asynchronously (if auto proxy is enabled).

        Returns:
            Whether the update was successful
        """
        # Acquire lock for thread safety if modifying shared state like proxy list
        with cls._lock:
            if not SWIFTSHADOW_AVAILABLE or not cls._initialized or not cls._auto_proxy_interface:
                return False

            try:
                # Use async version for integration with FastAPI
                await cls._auto_proxy_interface.async_update()
                print(f"Async proxy update successful, now have {len(cls._auto_proxy_interface.proxies)} proxies")
                # Reset index if list shrinks beyond current index
                if cls._current_proxy_index >= len(cls._auto_proxy_interface.proxies):
                    cls._current_proxy_index = -1
                return True
            except Exception as e:
                print(f"Error in async proxy update: {e}")
                return False

    @staticmethod
    def _extract_host_port(proxy_url: str) -> str:
        """Extract host:port from a proxy URL, removing protocol and credentials."""
        if not proxy_url:
            return ""
        try:
            # Remove protocol
            if '://' in proxy_url:
                proxy_url = proxy_url.split('://', 1)[1]

            # Remove credentials
            if '@' in proxy_url:
                proxy_url = proxy_url.split('@', 1)[1]

            # Remove trailing slash if present
            if proxy_url.endswith('/'):
                proxy_url = proxy_url[:-1]

            return proxy_url
        except Exception:
            # Fallback for unexpected formats
            return proxy_url

    # --- Keep helper methods for formatting if needed ---
    @staticmethod
    def format_proxy_url(host, port, username=None, password=None, protocol="http"):
        """Format a proxy URL with optional authentication."""
        auth_part = f"{username}:{password}@" if username and password else ""
        return f"{protocol}://{auth_part}{host}:{port}"

    @staticmethod
    def configure_proxy_with_auth(host, port, username=None, password=None):
        """Configure static proxy with separate authentication parameters."""
        proxy_settings = {
            'http': ProxyManager.format_proxy_url(host, port, username, password, "http"),
            'https': ProxyManager.format_proxy_url(host, port, username, password, "http") # Usually http for https traffic too
        }
        ProxyManager.configure_proxy(proxy_settings)
        return proxy_settings