import secrets

from pwdlib import PasswordHash

# PasswordHash.recommended() currently means Argon2
# recommended algorithm. If argon2 is ever superseded, updating pwdlib will change what "recommended" points to
# without having to change this code

password_hasher = PasswordHash.recommended()


def hash_password(plain_password: str) -> str:
  return password_hasher.hash(plain_password)



def verify_password(plain_password: str, hashed_password: str) -> bool:
  return password_hasher.verify(plain_password, hashed_password)


def create_session_token() -> str:
  """
  A random, unguessable string -> this is what goes in the cookie.
  token_urlsafe(32) gives ~256 bits of randomness, safe to put in URL / cookie
  """
  return secrets.token_urlsafe(32)









