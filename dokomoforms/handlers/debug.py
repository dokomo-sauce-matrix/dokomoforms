"""Pages pertaining to debug-specific functionality."""

from tornado.escape import json_encode
import tornado.web

from sqlalchemy.sql import exists
from sqlalchemy.orm.exc import NoResultFound

from dokomoforms.models import User, SurveyCreator, Email
from dokomoforms.handlers.util import BaseHandler


class DebugUserCreationHandler(BaseHandler):

    """User this page to create a user."""

    def get(self, email='test@test_email.com'):
        """Log in for any user (creating one if necessary)."""
        email_exists = (
            self.session
            .query(exists().where(Email.address == email))
            .scalar()
        )
        created = False
        if not email_exists:
            with self.session.begin():
                creator = SurveyCreator(
                    name='debug_user',
                    emails=[Email(address=email)],
                )
                self.session.add(creator)
            self.set_status(201)
            created = True
        DebugLoginHandler.get(self, email, created=created)


class DebugLoginHandler(BaseHandler):

    """Use this page to log in as any existing user."""

    def get(self, email="test@test_email.com", created=False):
        """Log in by supplying an e-mail address."""
        try:
            user = (
                self.session.query(User.id, User.name)
                .join(Email)
                .filter(Email.address == email)
                .one()
            )
            cookie_options = {
                'expires_days': None,
                'httponly': True,
            }
            self.set_secure_cookie(
                'user',
                json_encode({'user_id': user.id, 'user_name': user.name}),
                **cookie_options
            )
            response = {
                'email': email,
                'created': created,
            }
            self.write(response)
            self.finish()
        except NoResultFound:
            _ = self.locale.translate
            raise tornado.web.HTTPError(
                422,
                reason=_(
                    'There is no account associated with the e-mail'
                    ' address {}'.format(email)
                ),
            )


class DebugLogoutHandler(BaseHandler):

    """Log out by visiting this page."""

    def get(self):
        """Clear the 'user' cookie."""
        self.clear_cookie('user')
        self.write('You have logged out.')


class DebugPersonaHandler(BaseHandler):

    """For testing purposes there's no need to hit the real URL."""

    def check_xsrf_cookie(self):
        """No need for this..."""
        pass

    def post(self):
        """The test user has logged in."""
        self.write({'status': 'okay', 'email': 'test_creator@fixtures.com'})
