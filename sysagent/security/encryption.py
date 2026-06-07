import os
import logging
from cryptography.fernet import Fernet

logger = logging.getLogger("sysagent.security.encryption")

def _get_keystore_path() -> str:
    home = os.path.expanduser("~")
    sysagent_dir = os.path.join(home, ".sysagent")
    os.makedirs(sysagent_dir, exist_ok=True)
    return os.path.join(sysagent_dir, "keystore")

def get_or_create_key() -> bytes:
    """Retrieves existing Fernet key or initializes a new one securely."""
    key_path = _get_keystore_path()
    if os.path.exists(key_path):
        try:
            with open(key_path, "rb") as f:
                key = f.read().strip()
                if key:
                    return key
        except Exception as e:
            logger.error(f"Failed to read encryption key: {e}")
            
    # Generate new key
    logger.info("Generating new encryption key...")
    key = Fernet.generate_key()
    try:
        with open(key_path, "wb") as f:
            f.write(key)
        # Attempt chmod 600 (read/write only by owner)
        try:
            os.chmod(key_path, 0o600)
        except Exception as e:
            logger.debug(f"Could not apply chmod 600 to keystore on this platform: {e}")
    except Exception as e:
        logger.error(f"Failed to save encryption key to keystore: {e}")
        
    return key

def encrypt_data(data: str) -> bytes:
    """Encrypts clear text using the system's Fernet key."""
    key = get_or_create_key()
    f = Fernet(key)
    return f.encrypt(data.encode("utf-8"))

def decrypt_data(encrypted_bytes: bytes) -> str:
    """Decrypts ciphertext using the system's Fernet key."""
    key = get_or_create_key()
    f = Fernet(key)
    return f.decrypt(encrypted_bytes).decode("utf-8")

def encrypt_file(file_path: str, content: str) -> None:
    """Writes content to file_path encrypted."""
    try:
        enc_data = encrypt_data(content)
        with open(file_path, "wb") as f:
            f.write(enc_data)
        logger.info(f"Encrypted report saved successfully to {file_path}")
    except Exception as e:
        logger.error(f"Failed to write encrypted file {file_path}: {e}")
        raise e

def decrypt_report(file_path: str) -> str:
    """Reads and decrypts an encrypted report file."""
    try:
        with open(file_path, "rb") as f:
            enc_data = f.read()
        return decrypt_data(enc_data)
    except Exception as e:
        logger.error(f"Failed to decrypt report at {file_path}: {e}")
        raise e
