# gemini_handler/cli.py

import argparse
import os
from pathlib import Path
from typing import Dict, List, Optional

import yaml

from .data_models import KeyRotationStrategy, Strategy
from .server import GeminiServer


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Run Gemini API Server")
    parser.add_argument(
        "--host", 
        type=str, 
        default="0.0.0.0", 
        help="Host to bind server (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port", 
        type=int, 
        default=8000, 
        help="Port to bind server (default: 8000)"
    )
    parser.add_argument(
        "--keys", 
        type=str, 
        default=None,
        help="Comma-separated list of Gemini API keys"
    )
    parser.add_argument(
        "--config", 
        type=str, 
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)"
    )
    parser.add_argument(
        "--auto-proxy",
        action="store_true",
        help="Enable auto proxy rotation (requires SwiftShadow)"
    )
    
    return parser.parse_args()

def load_config(config_path: str) -> Dict:
    """Load configuration from YAML file."""
    try:
        config_path = Path(config_path)
        if config_path.exists():
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
                print(f"✓ Loaded configuration from {config_path}")
                return config
        else:
            print(f"! Config file {config_path} not found, using default settings")
            return {}
    except Exception as e:
        print(f"! Error loading config file: {e}")
        return {}

def main():
    """Main entry point for the CLI."""
    args = parse_args()
    
    # Load configuration
    config = load_config(args.config)
    
    # Process API keys (priority: CLI args > config file > env vars)
    api_keys = None
    if args.keys:
        api_keys = [k.strip() for k in args.keys.split(',') if k.strip()]
    elif config and 'gemini' in config and 'api_keys' in config['gemini']:
        api_keys = config['gemini']['api_keys']
    
    # Extract server settings from config
    server_settings = {}
    if config and 'gemini' in config:
        gemini_config = config['gemini']
        
        # Extract generation settings
        if 'generation' in gemini_config:
            server_settings['generation_config'] = gemini_config['generation']
        
        # Extract strategy settings
        if 'strategies' in gemini_config:
            strategies = gemini_config['strategies']
            if 'content' in strategies:
                content_strategy_map = {
                    'round_robin': Strategy.ROUND_ROBIN,
                    'fallback': Strategy.FALLBACK,
                    'retry': Strategy.RETRY
                }
                server_settings['content_strategy'] = content_strategy_map.get(
                    strategies['content'], Strategy.ROUND_ROBIN
                )
                
            if 'key_rotation' in strategies:
                key_rotation_map = {
                    'sequential': KeyRotationStrategy.SEQUENTIAL,
                    'round_robin': KeyRotationStrategy.ROUND_ROBIN,
                    'least_used': KeyRotationStrategy.LEAST_USED,
                    'smart_cooldown': KeyRotationStrategy.SMART_COOLDOWN
                }
                server_settings['key_strategy'] = key_rotation_map.get(
                    strategies['key_rotation'], KeyRotationStrategy.ROUND_ROBIN
                )
        
        # Extract rate limiting settings
        if 'rate_limits' in gemini_config:
            rate_limits = gemini_config['rate_limits']
            if 'requests_per_minute' in rate_limits:
                server_settings['rate_limit'] = rate_limits['requests_per_minute']
            if 'reset_window' in rate_limits:
                server_settings['reset_window'] = rate_limits['reset_window']
        
        # Extract retry settings
        if 'retry' in gemini_config:
            retry = gemini_config['retry']
            if 'max_attempts' in retry:
                server_settings['max_retries'] = retry['max_attempts']
            if 'delay' in retry:
                server_settings['retry_delay'] = retry['delay']
        
        # Extract system instruction
        if 'system_instruction' in gemini_config:
            server_settings['system_instruction'] = gemini_config['system_instruction']
    
    # Extract proxy settings
    proxy_settings = None
    if config and 'proxy' in config:
        proxy_settings = config['proxy']
        
        # Check if auto-proxy is explicitly enabled via CLI
        if args.auto_proxy and 'auto_proxy' not in proxy_settings:
            proxy_settings['auto_proxy'] = {
                'auto_update': True,
                'auto_rotate': True,
                'update_interval': 15
            }
            print("✓ Auto proxy enabled via command line argument")
        
        # If auto_proxy is configured, check for SwiftShadow
        if 'auto_proxy' in proxy_settings:
            try:
                import swiftshadow
                print(f"✓ Auto proxy configuration: {proxy_settings['auto_proxy']}")
            except ImportError:
                print("! SwiftShadow not found. Install with: pip install swiftshadow")
                print("! Auto proxy features will be disabled")
                # Keep the regular proxy settings, just remove auto_proxy
                if 'auto_proxy' in proxy_settings:
                    del proxy_settings['auto_proxy']
    
    # Create and run server
    server = GeminiServer(
        api_keys=api_keys,
        host=args.host,
        port=args.port,
        proxy_settings=proxy_settings,
        **server_settings
    )
    
    # Print server info
    print(f"✓ Gemini API Server running at http://{args.host}:{args.port}")
    print("✓ API is compatible with OpenAI format")
    print("✓ Endpoints:")
    print("  - GET  /v1/models")
    print("  - POST /v1/chat/completions")
    print("  - POST /v1/embeddings")
    print("  - GET  /health")
    
    # Print proxy info
    if proxy_settings:
        if 'auto_proxy' in proxy_settings:
            print("✓ Using auto proxy rotation with SwiftShadow")
            print(f"  - Auto update: {proxy_settings['auto_proxy'].get('auto_update', False)}")
            print(f"  - Auto rotate: {proxy_settings['auto_proxy'].get('auto_rotate', True)}")
            print(f"  - Update interval: {proxy_settings['auto_proxy'].get('update_interval', 15)}s")
        else:
            print("✓ Using static proxy configuration")
            if 'http' in proxy_settings:
                # Redact credentials for display
                http_proxy = proxy_settings['http']
                if '@' in http_proxy:
                    protocol, rest = http_proxy.split('://', 1)
                    credentials, address = rest.split('@', 1)
                    print(f"  - HTTP proxy: {protocol}://[REDACTED]@{address}")
                else:
                    print(f"  - HTTP proxy: {http_proxy}")
    
    # Add proxy endpoints info
    print("✓ Proxy management endpoints:")
    print("  - GET  /v1/proxy/info")
    print("  - GET  /v1/proxy/stats")
    print("  - POST /v1/proxy/rotate")
    
    # Run the server
    server.run()

if __name__ == "__main__":
    main()
