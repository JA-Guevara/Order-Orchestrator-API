"""Generate an API key and its SHA-256 hash for api_clients.json."""
import hashlib
import secrets


def main() -> None:
    api_key = secrets.token_urlsafe(48)
    api_key_hash = hashlib.sha256(api_key.encode("utf-8")).hexdigest()

    print("API_KEY:", api_key)
    print("SHA256: ", api_key_hash)


if __name__ == "__main__":
    main()
