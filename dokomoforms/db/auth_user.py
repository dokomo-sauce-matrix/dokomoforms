"""Allow access to the auth_user table."""

from datetime import datetime, timedelta
from time import localtime
import uuid

from sqlalchemy import select
from sqlalchemy.sql.dml import Insert, Update
from sqlalchemy.engine import RowProxy, Connection
from passlib.hash import bcrypt_sha256

from dokomoforms.db import update_record, auth_user_table


def get_auth_user(connection: Connection, auth_user_id: str) -> RowProxy:
    """
    Get a record from the auth_user table identified by auth_user_id.

    :param connection: a SQLAlchemy Connection
    :param auth_user_id: primary key
    :return: the record
    """
    select_stmt = select([auth_user_table])
    where_stmt = select_stmt.where(
        auth_user_table.c.auth_user_id == auth_user_id)
    auth_user = connection.execute(where_stmt).first()

    if auth_user is None:
        raise UserDoesNotExistError(auth_user_id)

    return auth_user


def get_auth_user_by_email(connection: Connection, email: str) -> RowProxy:
    """
    Get a record from the auth_user table identified by e-mail.

    :param connection: a SQLAlchemy Connection
    :param email: the user's e-mail address
    :return: the record
    """
    select_stmt = select([auth_user_table])
    where_stmt = select_stmt.where(auth_user_table.c.email == email)
    auth_user = connection.execute(where_stmt).first()

    if auth_user is None:
        raise UserDoesNotExistError(email)

    return auth_user


def create_auth_user(*, email: str) -> Insert:
    """
    Create a user account in the database. Make sure to use a transaction!

    :param email: The user's e-mail address
    :return: The Insert object. Execute this!
    """
    return auth_user_table.insert().values(email=email)


def generate_api_token() -> str:
    """
    Uses UUID4 to generate an API token.

    :return: The token as an alphanumeric string.
    """
    return ''.join(char for char in str(uuid.uuid4()) if char.isalnum())


def verify_api_token(connection: Connection,
                     *,
                     token: str,
                     email: str) -> bool:
    """
    Checks whether the supplied API token is valid for the specified user.

    :param connection: a SQLAlchemy Connection
    :param token: the API token
    :param email: the e-mail address of the user
    :return: whether the token is correct and not expired
    """
    try:
        auth_user = get_auth_user_by_email(connection, email)
    except UserDoesNotExistError:
        return False
    token_is_fresh = auth_user.expires_on.timetuple() >= localtime()
    not_blank = auth_user.token != ''
    token_matches = not_blank and bcrypt_sha256.verify(token, auth_user.token)

    return token_is_fresh and token_matches


def set_api_token(*,
                  expiration=timedelta(days=60),
                  token: str,
                  auth_user_id: str) -> Update:
    """
    Set a new API token for the given user.

    :param expiration: how long the token will be valid, 60 days by default.
    :param token: the token to set. Use generate_api_token()
    :param auth_user_id: the id of the user
    :return: The Update object. Execute this!
    """
    hashed_token = bcrypt_sha256.encrypt(token)
    expiration_time = datetime.now() + expiration
    return update_record(auth_user_table,
                         'auth_user_id',
                         auth_user_id,
                         token=hashed_token,
                         expires_on=expiration_time)


class UserDoesNotExistError(Exception):
    """The supplied e-mail address is not in the database."""
    pass


class IncorrectPasswordError(Exception):
    """The supplied password's hash doesn't match what's in the database."""
    pass
