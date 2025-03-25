import secrets

secret_key = secrets.token_hex(32)  # Generates a 64-character hex key
print(secret_key)
