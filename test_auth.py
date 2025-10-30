#!/usr/bin/env python3
"""
Test script for simple password authentication.
This script helps verify that the authentication system is working correctly.
"""

import os
import sys

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.default import Default
from common.simple_auth import verify_password, is_route_protected

def test_configuration():
    """Test authentication configuration."""
    print("Testing Authentication Configuration...")
    print("=" * 50)
    
    cfg = Default()
    
    print(f"SIMPLE_AUTH_ENABLED: {cfg.SIMPLE_AUTH_ENABLED}")
    print(f"SIMPLE_AUTH_PASSWORD: {'*' * len(cfg.SIMPLE_AUTH_PASSWORD)}")
    print(f"SESSION_TIMEOUT: {cfg.SESSION_TIMEOUT} seconds")
    
    if not cfg.SIMPLE_AUTH_ENABLED:
        print("\n⚠️  WARNING: Simple authentication is DISABLED!")
        print("   Set SIMPLE_AUTH_ENABLED=true in your environment to enable it.")
        return False
    
    return True

def test_password_verification():
    """Test password verification."""
    print("\nTesting Password Verification...")
    print("=" * 50)
    
    cfg = Default()
    
    # Test correct password
    correct_result = verify_password(cfg.SIMPLE_AUTH_PASSWORD)
    print(f"Correct password verification: {'✅ PASS' if correct_result else '❌ FAIL'}")
    
    # Test incorrect password
    incorrect_result = verify_password("wrong_password")
    print(f"Incorrect password rejection: {'✅ PASS' if not incorrect_result else '❌ FAIL'}")
    
    return correct_result and not incorrect_result

def test_route_protection():
    """Test route protection logic."""
    print("\nTesting Route Protection...")
    print("=" * 50)
    
    test_cases = [
        ("/", True, "Root route should be protected"),
        ("/home", True, "Home route should be protected"),
        ("/about", True, "About route should be protected"),
        ("/login", False, "Login route should NOT be protected"),
        ("/api/login", False, "Login API should NOT be protected"),
        ("/static/style.css", False, "Static files should NOT be protected"),
        ("/assets/image.png", False, "Asset files should NOT be protected"),
        ("/favicon.ico", False, "Favicon should NOT be protected"),
    ]
    
    all_passed = True
    for path, should_be_protected, description in test_cases:
        is_protected = is_route_protected(path)
        passed = is_protected == should_be_protected
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} {path}: {description}")
        if not passed:
            all_passed = False
    
    return all_passed

def main():
    """Run all tests."""
    print("Simple Password Authentication Test Suite")
    print("========================================\n")
    
    tests = [
        ("Configuration", test_configuration),
        ("Password Verification", test_password_verification),
        ("Route Protection", test_route_protection),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ FAIL: {test_name} - Error: {e}")
            results.append((test_name, False))
    
    print("\nTest Results Summary:")
    print("=" * 50)
    all_passed = True
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} {test_name}")
        if not passed:
            all_passed = False
    
    print(f"\nOverall Result: {'✅ ALL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'}")
    
    if all_passed:
        print("\n🎉 Authentication system is ready!")
        print("\nTo enable authentication:")
        print("1. Set SIMPLE_AUTH_ENABLED=true in your environment")
        print("2. Set SIMPLE_AUTH_PASSWORD=your_password")
        print("3. Start the application")
        print("4. Visit any protected route - you'll be redirected to /login")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())