# Web3 Integration Module Routes

try:
    from .auth import auth_bp
    from .payments import payments_bp
    from .nft import nft_bp
    from .compliance import compliance_bp
except ImportError:
    # Fallback for standalone execution
    from routes.auth import auth_bp
    from routes.payments import payments_bp
    from routes.nft import nft_bp
    from routes.compliance import compliance_bp

__all__ = ['auth_bp', 'payments_bp', 'nft_bp', 'compliance_bp']