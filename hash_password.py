#!/usr/bin/env python3
"""Helper script: generate a bcrypt hash for GATEWAY_USERS JSON config.

Usage:
    python hash_password.py <plaintext_password>
"""
import sys
from passlib.context import CryptContext

ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
print(ctx.hash(sys.argv[1]))
