#!/usr/bin/env python3
"""Test script to verify configuration and MBTA API connection."""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'mbta_pipeline'))

from mbta_pipeline.config.settings import settings
import requests
import json


def test_configuration():
    """Test that all configuration values are loaded correctly."""
    print("🔧 Testing Configuration...")
    print(f"MBTA API Key: {settings.mbta_api_key[:8]}...{settings.mbta_api_key[-4:]}")
    print(f"MBTA Base URL: {settings.mbta_base_url}")
    print(f"Database URL: {settings.database_url}")
    print(f"Redis URL: {settings.redis_url}")
    print(f"Log Level: {settings.log_level}")
    print(f"Environment: {settings.environment}")
    print("✅ Configuration loaded successfully!\n")


def test_mbta_api_connection():
    """Test connection to MBTA API."""
    print("🚇 Testing MBTA API Connection...")
    
    headers = {
        'Authorization': f'Bearer {settings.mbta_api_key}',
        'Accept': 'application/json'
    }
    
    try:
        # Test with a simple endpoint - get routes
        url = f"{settings.mbta_base_url}{settings.mbta_endpoint_routes}"
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ API Connection successful!")
            print(f"   Found {len(data.get('data', []))} routes")
            print(f"   Response time: {response.elapsed.total_seconds():.2f}s")
        else:
            print(f"❌ API request failed with status {response.status_code}")
            print(f"   Response: {response.text[:200]}...")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ API Connection failed: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
    
    print()


def test_mbta_endpoints():
    """Test various MBTA API endpoints."""
    print("🔍 Testing MBTA API Endpoints...")
    
    headers = {
        'Authorization': f'Bearer {settings.mbta_api_key}',
        'Accept': 'application/json'
    }
    
    endpoints = [
        ('/routes', 'Routes'),
        ('/stops', 'Stops'),
        ('/vehicles', 'Vehicles'),
        ('/predictions', 'Predictions')
    ]
    
    for endpoint, name in endpoints:
        try:
            url = f"{settings.mbta_base_url}{endpoint}"
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                count = len(data.get('data', []))
                print(f"   ✅ {name}: {count} items")
            else:
                print(f"   ❌ {name}: HTTP {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ {name}: {e}")
    
    print()


if __name__ == "__main__":
    print("🚀 MBTA Pipeline Configuration Test\n")
    
    try:
        test_configuration()
        test_mbta_api_connection()
        test_mbta_endpoints()
        
        print("🎉 All tests completed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        sys.exit(1)
