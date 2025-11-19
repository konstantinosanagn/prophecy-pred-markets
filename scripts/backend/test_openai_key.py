#!/usr/bin/env python
"""Test script to verify OpenAI API key is valid."""

import sys
from pathlib import Path

# Add backend directory to path to import app modules
backend_dir = Path(__file__).parent.parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from app.config import settings
from app.services.openai_client import get_openai_client


def test_openai_key():
    """Test if OpenAI API key is valid by making a simple API call."""
    print("Testing OpenAI API Key...")
    print(f"Key found: {'Yes' if settings.openai_api_key else 'No'}")

    if not settings.openai_api_key:
        print("ERROR: OPENAI_API_KEY not found in environment variables")
        print("   Make sure your .env file is in the project root and contains:")
        print("   OPENAI_API_KEY=sk-your-key-here")
        return False

    # Show first and last few characters for verification (not the full key)
    key_preview = settings.openai_api_key[:7] + "..." + settings.openai_api_key[-4:]
    print(f"Key preview: {key_preview}")
    print(f"Key length: {len(settings.openai_api_key)} characters")

    # Check for common issues
    if settings.openai_api_key.startswith("your_actual_openai_api_key"):
        print("ERROR: You're using the placeholder value!")
        print("   Please replace it with your actual OpenAI API key")
        return False

    if len(settings.openai_api_key) < 20:
        print("WARNING: Key seems too short (should be ~50+ characters)")

    # Try to initialize the client
    try:
        openai_client = get_openai_client()
        if not openai_client.client and not openai_client.api_key:
            print("ERROR: OpenAI client initialization failed")
            return False

        client_status = "Yes" if openai_client.client or openai_client.api_key else "No"
        print(f"Client initialized: {client_status}")
        print(f"Using new API format: {openai_client._use_new_api}")

        # Make a simple test API call
        print("\nMaking test API call...")
        if openai_client.client and openai_client._use_new_api:
            # New API format
            completion = openai_client.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "user", "content": "Say 'test successful' if you can read this."}
                ],
                max_tokens=10,
            )
            response = completion.choices[0].message.content
        else:
            # Old API format (fallback)
            import openai

            openai.api_key = openai_client.api_key
            completion = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "user", "content": "Say 'test successful' if you can read this."}
                ],
                max_tokens=10,
            )
            response = completion.choices[0].message["content"]

        print("SUCCESS! API key is valid.")
        print(f"   Response: {response}")
        return True

    except Exception as e:
        error_msg = str(e)
        print("\nERROR: API call failed")
        print(f"   Error: {error_msg}")

        if "401" in error_msg or "Unauthorized" in error_msg or "invalid_api_key" in error_msg:
            print("\n   This means your API key is invalid or incorrect.")
            print("   Please check:")
            print("   1. Your key is correct in the .env file")
            print("   2. No extra spaces or newlines")
            print("   3. The key hasn't been revoked")
            print("   4. Get a new key from: https://platform.openai.com/api-keys")
        elif "rate_limit" in error_msg.lower():
            print("\n   Rate limit exceeded - but key is valid!")
            return True
        else:
            print("\n   Unexpected error. Check your internet connection and try again.")

        return False


if __name__ == "__main__":
    success = test_openai_key()
    sys.exit(0 if success else 1)
