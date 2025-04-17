#!/usr/bin/env python3
# test_proxy_control.py

import os
from pathlib import Path

from gemini_handler import GeminiHandler

# --- Configuration ---
CONFIG_FILE = "../config.yaml"  # Your config file with proxy settings
PROMPT = "Viết một đoạn văn ngắn về bầu trời xanh."

# ANSI color codes for better output
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RED = "\033[91m"
RESET = "\033[0m"

def print_header(text):
    """Print a formatted header."""
    print(f"\n{BLUE}{'=' * 80}{RESET}")
    print(f"{BLUE}== {text}{RESET}")
    print(f"{BLUE}{'=' * 80}{RESET}\n")

def test_with_handler(handler, description):
    """Test content generation with the given handler."""
    print(f"{YELLOW}Testing: {description}{RESET}")
    
    try:
        print("Generating content...")
        response = handler.generate_content(
            prompt=PROMPT,
            return_stats=True
        )
        
        print("\n--- Response ---")
        if response['success']:
            print(f"{GREEN}✓ Success!{RESET}")
            print(f"Model Response:\n{response['text'][:200]}...")
            print("-" * 50)
            print(f"Model Used: {response['model']}")
            print(f"Time Taken: {response['time']:.2f}s")
            print(f"API Key Index Used: {response['api_key_index']}")
        else:
            print(f"{RED}✗ Failure!{RESET}")
            print(f"Error: {response['error']}")
            print(f"Model Tried: {response['model']}")
            print(f"API Key Index Tried: {response['api_key_index']}")
        
        print("-" * 50)
        return response['success']
        
    except Exception as e:
        print(f"{RED}✗ Exception occurred: {e}{RESET}")
        return False

def main():
    print_header("Gemini Handler Proxy Control Test")
    
    if not os.path.exists(CONFIG_FILE):
        print(f"{RED}Error: Configuration file '{CONFIG_FILE}' not found!{RESET}")
        return
    
    # Test 1: With proxy from config
    print_header("Test 1: Using Proxy from Config")
    try:
        handler_with_proxy = GeminiHandler(config_path=CONFIG_FILE)
        print(f"Proxy settings: {handler_with_proxy.proxy_settings}")
        success1 = test_with_handler(handler_with_proxy, "Using proxy from config file")
    except Exception as e:
        print(f"{RED}Failed to initialize handler: {e}{RESET}")
        success1 = False
    
    # Test 2: Without proxy (explicitly disabled)
    print_header("Test 2: Explicitly Disabling Proxy")
    try:
        handler_no_proxy = GeminiHandler(
            config_path=CONFIG_FILE,
            proxy_settings=None  # Explicitly disable proxy
        )
        print(f"Proxy settings: {handler_no_proxy.proxy_settings}")
        success2 = test_with_handler(handler_no_proxy, "Explicitly disabled proxy")
    except Exception as e:
        print(f"{RED}Failed to initialize handler: {e}{RESET}")
        success2 = False
    
    # Summary
    print_header("Test Summary")
    print(f"Test 1 (With Proxy): {'✓ Passed' if success1 else '✗ Failed'}")
    print(f"Test 2 (No Proxy): {'✓ Passed' if success2 else '✗ Failed'}")
    
    if success1 and success2:
        print(f"\n{GREEN}Both tests passed! Proxy control is working correctly.{RESET}")
    elif success1:
        print(f"\n{YELLOW}Only the proxy test passed. Direct connection failed.{RESET}")
    elif success2:
        print(f"\n{YELLOW}Only the direct connection passed. Proxy connection failed.{RESET}")
    else:
        print(f"\n{RED}Both tests failed. Check your API keys and network configuration.{RESET}")

if __name__ == "__main__":
    main()
