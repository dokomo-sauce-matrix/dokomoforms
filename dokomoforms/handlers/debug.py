"""Pages pertaining to debug-specific functionality."""
from tornado.escape import json_encode, json_decode
import tornado.web

from sqlalchemy.sql import exists
from sqlalchemy.orm.exc import NoResultFound

from dokomoforms.options import options
from dokomoforms.models import User, Administrator, Email
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
                creator = Administrator(
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


if options.dev or options.debug:  # pragma: no cover
    import lzstring
    revisit_online = True
    facilities_file = 'tests/python/fake_revisit_facilities.json'
    with open(facilities_file, 'rb') as facilities:
        compressed_facilities = facilities.read()
    lzs = lzstring.LZString()


class DebugRevisitHandler(BaseHandler):

    """For testing purposes there's no need to hit Revisit proper."""

    def check_xsrf_cookie(self):
        """Debug endpoint."""
        return None

    def get(self):
        """Get dummy facilities."""
        if not revisit_online:
            raise tornado.web.HTTPError(502)
        self.write(compressed_facilities)
        self.set_header('Content-Type', 'application/json')

    def post(self):
        """Add a facility."""
        global compressed_facilities
        if not revisit_online:
            raise tornado.web.HTTPError(502)
        new_facility = json_decode(self.request.body)
        c_facilities_json = json_decode(compressed_facilities)
        facility_data = (
            c_facilities_json['facilities']['children']['wn']['data'][0]
        )
        uncompressed = json_decode(lzs.decompressFromUTF16(facility_data))
        uncompressed.append({
            '_version': 0,
            'active': True,
            'coordinates': new_facility['coordinates'],
            'createdAt': '2014-04-23T20:32:20.043Z',
            'href': (
                'http://localhost:3000/api/v0/facilities/{}.json'.format(
                    new_facility['uuid']
                )
            ),
            'identifiers': [],
            'name': new_facility['name'],
            'properties': new_facility['properties'],
            'updatedAt': '2014-04-23T20:32:20.043Z',
            'uuid': new_facility['uuid'],
        })
        compressed = lzs.compressToUTF16(json_encode(uncompressed))
        c_facilities_json['facilities']['children']['wn']['data'] = [
            compressed
        ]
        compressed_facilities = json_encode(c_facilities_json).encode()
        self.set_status(201)


class DebugToggleRevisitHandler(BaseHandler):

    """For turning the fake Revisit endpoint off and on."""

    def get(self):
        """Toggle the 'online' state of the GET endpoint."""
        global revisit_online
        global compressed_facilities
        state_arg = self.get_argument('state', None)
        if state_arg:
            if state_arg == 'true':
                revisit_online = True
                with open(facilities_file, 'rb') as facilities:
                    compressed_facilities = facilities.read()
            else:
                revisit_online = False
        else:
            revisit_online = not revisit_online
