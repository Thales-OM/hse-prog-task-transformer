from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend
import datetime
from typing import Optional, Literal
from src.exceptions import UnauthorizedException, PublicKeyMissingException
from src.config import settings
from src.schemas import RSAKeyPair, PostRenewTokenResponse
from src.logger import LoggerFactory
from src.utils import key_to_form


logger = LoggerFactory.getLogger(__name__)


def generate_rsa_key_pair() -> RSAKeyPair:
    # Generate private key
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048
    )

    # Get public key from private key
    public_key = private_key.public_key()

    # Serialize keys if needed
    private_pem_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )

    public_pem_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )

    # Convert bytes to strings
    private_pem_str = private_pem_bytes.decode('utf-8')
    public_pem_str = public_pem_bytes.decode('utf-8')

    return RSAKeyPair(public_pem=public_pem_str, private_pem=private_pem_str)


def verify_rsa_key_pair(private_pem: bytes | str, public_pem: bytes | str) -> bool:
    """
    Verify that an RSA private key and public key PEM pair are matched.
    
    Args:
        private_pem: Private key in PEM format (bytes) or string
        public_pem: Public key in PEM format (bytes) or string
    
    Returns:
        bool: True if keys are matched, False otherwise
    """
    try:
        if isinstance(private_pem, str):
            # Convert string to bytes
            private_pem = private_pem.encode()
        
        # Load the private key from PEM
        private_key = serialization.load_pem_private_key(
            private_pem,
            password=None,
            backend=default_backend()
        )
        
        # Verify the private key is actually an RSA key
        if not isinstance(private_key, rsa.RSAPrivateKey):
            raise ValueError("Private key is not an RSA key")
        
        if isinstance(public_pem, str):
            # Convert string to bytes
            public_pem = public_pem.encode()
        
        # Load the public key from PEM
        public_key = serialization.load_pem_public_key(
            public_pem,
            backend=default_backend()
        )
        
        # Verify the public key is actually an RSA key
        if not isinstance(public_key, rsa.RSAPublicKey):
            raise ValueError("Public key is not an RSA key")
        
        # Create test message
        test_message = b"Test message for RSA key verification"
        
        # Sign with private key
        signature = private_key.sign(
            test_message,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        
        # Verify with public key
        public_key.verify(
            signature,
            test_message,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        
        return True
    
    except Exception as e:
        logger.warning(f"Key verification failed: {str(e)}")
        return False


def renew_auth_token() -> PostRenewTokenResponse:
    key_pair = generate_rsa_key_pair()
    settings.server.set_public_api_key(public_pem=key_pair.public_pem)
    private_pem_string = key_to_form(text=key_pair.private_pem)
    return PostRenewTokenResponse(private_pem=private_pem_string)