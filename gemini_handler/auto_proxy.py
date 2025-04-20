# gemini_handler/auto_proxy.py

import asyncio
import threading
import time
from typing import Any, Dict, List, Optional, Union

# Check if SwiftShadow is available
try:
    from swiftshadow.classes import Proxy, ProxyInterface
    SWIFTSHADOW_AVAILABLE = True
except ImportError:
    SWIFTSHADOW_AVAILABLE = False
    print("SwiftShadow library not available. Install with: pip install swiftshadow")
    # Create dummy Proxy class for type hints when SwiftShadow isn't available
    class Proxy:
        def as_string(self) -> str:
            return ""


class AutoProxyManager:
    """Manages automatic proxy updates and rotation using SwiftShadow."""
    
    # Singleton instance and state variables
    _instance = None
    _lock = threading.RLock()
    _proxy_interface = None
    _update_thread = None
    _current_index = 0
    _update_interval = 15
    _auto_update = False
    _auto_rotate = True
    _initialized = False
    _last_update = 0
    _current_proxy = None  # Track the current proxy
    _proxy_history = []    # Keep a history of recently used proxies
    
    @classmethod
    def get_instance(cls) -> 'AutoProxyManager':
        """Get or create the singleton instance."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = AutoProxyManager()
            return cls._instance
    
    @classmethod
    def is_available(cls) -> bool:
        """Check if SwiftShadow is available."""
        return SWIFTSHADOW_AVAILABLE
    
    @classmethod
    def initialize(
        cls,
        auto_update: bool = False,
        auto_rotate: bool = True,
        update_interval: int = 15
    ) -> bool:
        """
        Initialize the auto proxy system.
        
        Args:
            auto_update: Whether to automatically update proxies
            auto_rotate: Whether to rotate through proxies
            update_interval: Seconds between proxy updates
            
        Returns:
            Whether initialization was successful
        """
        if not SWIFTSHADOW_AVAILABLE:
            print("SwiftShadow library not available. Install with: pip install swiftshadow")
            return False
        
        with cls._lock:
            cls._auto_update = auto_update
            cls._auto_rotate = auto_rotate
            cls._update_interval = update_interval
            
            if cls._proxy_interface is None:
                cls._proxy_interface = ProxyInterface(autoUpdate=False, autoRotate=False)
                
                # Initial proxy update
                try:
                    cls._proxy_interface.update()
                    cls._last_update = time.time()
                    cls._initialized = True
                    print(f"Initial proxy update successful, got {len(cls._proxy_interface.proxies)} proxies")
                except Exception as e:
                    print(f"Failed initial proxy update: {e}")
                    return False
                
                # Start background update thread if auto_update is enabled
                if auto_update and cls._update_thread is None:
                    cls._start_update_thread()
            
            return cls._initialized
    
    @classmethod
    def _start_update_thread(cls) -> None:
        """Start a background thread for periodic proxy updates."""
        def update_proxies():
            while True:
                try:
                    time.sleep(cls._update_interval)
                    with cls._lock:
                        if cls._proxy_interface and cls._auto_update:
                            print(f"Updating proxies... (interval: {cls._update_interval}s)")
                            cls._proxy_interface.update()
                            cls._last_update = time.time()
                            print(f"Proxy update successful, now have {len(cls._proxy_interface.proxies)} proxies")
                except Exception as e:
                    print(f"Error updating proxies: {e}")
                    time.sleep(5)  # Back off on error
        
        cls._update_thread = threading.Thread(target=update_proxies, daemon=True)
        cls._update_thread.start()
        print("Started proxy update background thread")
    
    @classmethod
    def get_next_proxy(cls) -> Optional[Dict[str, str]]:
        # Maintain a current index to force rotation
        if not hasattr(cls, '_proxy_index'):
            cls._proxy_index = 0
        
        if not cls._initialized or not cls._auto_proxy_interface:
            return None
        
        with cls._lock:
            if not cls._proxy_interface.proxies:
                return None
            
            # Directly select a proxy by index to ensure rotation
            if cls._auto_rotate and cls._proxy_interface.proxies:
                proxies = cls._proxy_interface.proxies
                cls._proxy_index = (cls._proxy_index + 1) % len(proxies)
                proxy = proxies[cls._proxy_index]
            else:
                proxy = cls._proxy_interface.get()
    
    @classmethod
    async def async_update(cls) -> bool:
        """
        Update proxies asynchronously.
        
        Returns:
            Whether the update was successful
        """
        if not cls._initialized or not cls._proxy_interface:
            return False
        
        try:
            # Use async version for integration with FastAPI
            await cls._proxy_interface.async_update()
            cls._last_update = time.time()
            print(f"Async proxy update successful, now have {len(cls._proxy_interface.proxies)} proxies")
            return True
        except Exception as e:
            print(f"Error in async proxy update: {e}")
            return False
    
    @classmethod
    def get_current_proxy(cls) -> Optional[Dict[str, Any]]:
        """
        Get information about the currently used proxy.
        
        Returns:
            Dictionary with current proxy info or None
        """
        with cls._lock:
            return cls._current_proxy
    
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
    def get_stats(cls) -> Dict[str, Any]:
        """
        Get proxy stats.
        
        Returns:
            Dictionary with proxy stats
        """
        with cls._lock:
            return {
                'initialized': cls._initialized,
                'auto_update': cls._auto_update,
                'auto_rotate': cls._auto_rotate,
                'update_interval': cls._update_interval,
                'last_update': cls._last_update,
                'proxy_count': len(cls._proxy_interface.proxies) if cls._proxy_interface else 0,
                'current_proxy': cls._current_proxy,
                'proxy_history': cls._proxy_history
            }
