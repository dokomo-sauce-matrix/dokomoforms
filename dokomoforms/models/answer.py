"""Answer models."""

import abc
from collections import OrderedDict

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg
from sqlalchemy.orm import relationship, synonym, column_property
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.sql import func
# from sqlalchemy.sql.type_api import UserDefinedType

from geoalchemy2 import Geometry

from dokomoforms.models import util, Base, node_type_enum
from dokomoforms.exc import NotAnAnswerTypeError, NotAResponseTypeError


class Answer(Base):

    """An Answer is a response to a SurveyNode.

    An Answer can be one of an answer, an "other" response or a "don't know"
    response. Answer.response abstracts over these 3 possibilites.
    """

    __tablename__ = 'answer'

    id = util.pk()
    answer_number = sa.Column(sa.Integer, nullable=False)
    submission_id = sa.Column(pg.UUID, nullable=False)
    submission_time = sa.Column(pg.TIMESTAMP(timezone=True), nullable=False)
    survey_id = sa.Column(pg.UUID, nullable=False)
    survey_node_id = sa.Column(pg.UUID, nullable=False)
    survey_node = relationship('AnswerableSurveyNode')
    allow_multiple = sa.Column(sa.Boolean, nullable=False)
    allow_other = sa.Column(sa.Boolean, nullable=False)
    allow_dont_know = sa.Column(sa.Boolean, nullable=False)
    question_id = sa.Column(pg.UUID, nullable=False)
    type_constraint = sa.Column(node_type_enum, nullable=False)
    answer_type = sa.Column(
        sa.Enum(
            'text', 'photo', 'integer', 'decimal', 'date', 'time',
            'timestamp', 'location', 'facility', 'multiple_choice',
            name='answer_type_name',
            inherit_schema=True,
            metadata=Base.metadata,
        ),
        nullable=False,
    )
    last_update_time = util.last_update_time()

    @property
    @abc.abstractmethod
    def main_answer(self):
        """The representative part of a provided answer.

        The main_answer is the only answer for simple types (integer, text,
        etc.) and for other types is the part of the answer that is most
        important. In practice, the main_answer is special only in that all
        Answer models have it, which is necessary for certain constraints and
        for the response property.
        """

    @property
    @abc.abstractmethod
    def answer(self):
        """The answer. Could be the same as main_answer in simple cases.

        This property is the most useful representation available of the
        answer. In the simplest case it is just a synonym for main_answer.
        It could otherwise be a dictionary or another model.
        """

    @property
    @abc.abstractmethod
    def other(self):
        """A text field containing "other" responses."""

    @property
    @abc.abstractmethod
    def dont_know(self):
        """A text field containing "don't know" responses."""

    @hybrid_property
    def response(self) -> OrderedDict:
        """A dictionary that abstracts over answer, other, and dont_know.

        {
            'response_type': 'answer|other|dont_know',
            'response': <one of self.answer, self.other, self.dont_know>
        }
        """
        possible_responses = [
            ('answer', self.main_answer),
            ('other', self.other),
            ('dont_know', self.dont_know),
        ]
        response_type, response = next(
            p_r for p_r in possible_responses if p_r[1] is not None
        )
        if response_type == 'answer':
            if self.type_constraint == 'multiple_choice':
                response = self.choice
            else:
                response = self.answer
        return OrderedDict((
            ('response_type', response_type),
            ('response', response),
        ))

    @response.setter
    def response(self, response_dict):
        """Set the appropriate field using the response dict."""
        response_type = response_dict['response_type']
        if response_type not in {'answer', 'other', 'dont_know'}:
            raise NotAResponseTypeError(response_type)
        setattr(self, response_type, response_dict['response'])

    __mapper_args__ = {'polymorphic_on': answer_type}
    __table_args__ = (
        sa.UniqueConstraint('id', 'allow_other', 'allow_dont_know'),
        sa.UniqueConstraint(
            'id', 'allow_other', 'allow_dont_know', 'survey_node_id',
            'question_id', 'submission_id',
        ),
        sa.CheckConstraint('type_constraint::TEXT = answer_type::TEXT'),
        sa.ForeignKeyConstraint(
            ['submission_id', 'submission_time', 'survey_id'],
            ['submission.id', 'submission.submission_time',
                'submission.survey_id']
        ),
        sa.ForeignKeyConstraint(
            [
                'survey_node_id',
                'question_id',
                'type_constraint',
                'allow_multiple',
                'allow_other',
                'allow_dont_know',
            ],
            [
                'survey_node_answerable.id',
                'survey_node_answerable.the_node_id',
                'survey_node_answerable.the_type_constraint',
                'survey_node_answerable.allow_multiple',
                'survey_node_answerable.allow_other',
                'survey_node_answerable.allow_dont_know',
            ]
        ),
        sa.Index(
            'only_one_answer_allowed',
            'survey_node_id', 'submission_id',
            unique=True,
            postgresql_where=sa.not_(allow_multiple),
        ),
    )

    def _asdict(self) -> OrderedDict:
        return OrderedDict((
            ('id', self.id),
            ('deleted', self.deleted),
            ('answer_number', self.answer_number),
            ('submission_id', self.submission_id),
            ('submission_time', self.submission_time),
            ('survey_id', self.survey_id),
            ('survey_node_id', self.survey_node_id),
            ('question_id', self.question_id),
            ('type_constraint', self.type_constraint),
            ('last_update_time', self.last_update_time),
            ('response', self.response),
        ))


class _AnswerMixin:
    id = util.pk()
    the_allow_other = sa.Column(sa.Boolean, nullable=False)
    the_allow_dont_know = sa.Column(sa.Boolean, nullable=False)

    other = sa.Column(pg.TEXT)
    dont_know = sa.Column(pg.TEXT)


def _answer_mixin_table_args():
    return (
        sa.ForeignKeyConstraint(
            ['id', 'the_allow_other', 'the_allow_dont_know'],
            ['answer.id', 'answer.allow_other', 'answer.allow_dont_know']
        ),
        sa.CheckConstraint(
            # "other" responses are allowed XOR other is null
            """
            the_allow_other != (other IS NULL)
            """,
            name='check_whether_other_is_allowed'
        ),
        sa.CheckConstraint(
            # "dont_know" responses are allowed XOR dont_know is null
            """
            the_allow_dont_know != (dont_know IS NULL)
            """,
            name='check_whether_dont_know_is_allowed'
        ),
        sa.CheckConstraint(
            """
            (CASE WHEN (main_answer IS NOT NULL) AND
                       (other       IS     NULL) AND
                       (dont_know   IS     NULL)
                THEN 1 ELSE 0 END) +
            (CASE WHEN (main_answer IS     NULL) AND
                       (other       IS NOT NULL) AND
                       (dont_know   IS     NULL)
                THEN 1 ELSE 0 END) +
            (CASE WHEN (main_answer IS     NULL) AND
                       (other       IS     NULL) AND
                       (dont_know   IS NOT NULL)
                THEN 1 ELSE 0 END) =
            1
            """,
            name='only_one_answer_type_check'
        ),
    )


class TextAnswer(_AnswerMixin, Answer):

    """A TEXT answer."""

    __tablename__ = 'answer_text'
    main_answer = sa.Column(pg.TEXT)
    answer = synonym('main_answer')
    __mapper_args__ = {'polymorphic_identity': 'text'}
    __table_args__ = _answer_mixin_table_args()


class PhotoAnswer(_AnswerMixin, Answer):

    """A photo answer (the id of a Photo)."""

    __tablename__ = 'answer_photo'
    main_answer = sa.Column(pg.UUID, util.fk('photo.id'))
    answer = synonym('main_answer')
    photo = relationship('Photo')
    __mapper_args__ = {'polymorphic_identity': 'photo'}
    __table_args__ = _answer_mixin_table_args()

    def _asdict(self) -> OrderedDict:
        result = super()._asdict()
        result['photo'] = self.photo
        return result


# class LObject(UserDefinedType):
#     def get_col_spec(self):
#         return "lo"


class Photo(Base):

    """A BYTEA holding an image."""

    __tablename__ = 'photo'

    id = util.pk()
    image = sa.Column(pg.BYTEA, nullable=False)
    # image = sa.Column(LObject)

    def _asdict(self) -> OrderedDict:
        return OrderedDict((
            ('id', self.id),
            ('deleted', self.deleted),
            ('image', self.image),
        ))


# sa.event.listen(
#     Photo.__table__,
#     'after_create',
#     sa.DDL(
#         'CREATE TRIGGER t_image BEFORE UPDATE OR DELETE ON photo'
#         ' FOR EACH ROW EXECUTE PROCEDURE lo_manage(image)'
#     ),
# )


class IntegerAnswer(_AnswerMixin, Answer):

    """An INTEGER answer (signed 4 byte)."""

    __tablename__ = 'answer_integer'
    main_answer = sa.Column(sa.Integer)
    answer = synonym('main_answer')
    __mapper_args__ = {'polymorphic_identity': 'integer'}
    __table_args__ = _answer_mixin_table_args()


class DecimalAnswer(_AnswerMixin, Answer):

    """A NUMERIC answer."""

    __tablename__ = 'answer_decimal'
    main_answer = sa.Column(pg.NUMERIC)
    answer = synonym('main_answer')
    __mapper_args__ = {'polymorphic_identity': 'decimal'}
    __table_args__ = _answer_mixin_table_args()


class DateAnswer(_AnswerMixin, Answer):

    """A DATE answer."""

    __tablename__ = 'answer_date'
    main_answer = sa.Column(sa.Date)
    answer = synonym('main_answer')
    __mapper_args__ = {'polymorphic_identity': 'date'}
    __table_args__ = _answer_mixin_table_args()


class TimeAnswer(_AnswerMixin, Answer):

    """A TIME WITH TIME ZONE answer."""

    __tablename__ = 'answer_time'
    main_answer = sa.Column(sa.Time(timezone=True))
    answer = synonym('main_answer')
    __mapper_args__ = {'polymorphic_identity': 'time'}
    __table_args__ = _answer_mixin_table_args()


class TimestampAnswer(_AnswerMixin, Answer):

    """A TIMESTAMP WITH TIME ZONE answer."""

    __tablename__ = 'answer_timestamp'
    main_answer = sa.Column(pg.TIMESTAMP(timezone=True))
    answer = synonym('main_answer')
    __mapper_args__ = {'polymorphic_identity': 'timestamp'}
    __table_args__ = _answer_mixin_table_args()


class LocationAnswer(_AnswerMixin, Answer):

    """A GEOMETRY('POINT', 4326) answer.

    Accepts input in the form
    {
        'lng': <longitude>,
        'lat': <latitude>
    }

    The output is a GeoJSON.
    """

    __tablename__ = 'answer_location'
    main_answer = sa.Column(Geometry('POINT', 4326))
    geo_json = column_property(func.ST_AsGeoJSON(main_answer))

    @hybrid_property
    def answer(self):
        """LocationAnswer.geo_json."""
        return self.geo_json

    @answer.setter
    def answer(self, location: dict):
        """Set LocationAnswer.main_answer using a dict of lng and lat."""
        self.main_answer = 'SRID=4326;POINT({lng} {lat})'.format(**location)

    __mapper_args__ = {'polymorphic_identity': 'location'}
    __table_args__ = _answer_mixin_table_args()


class FacilityAnswer(_AnswerMixin, Answer):

    """A facility answer (a la Revisit).

    FacilityAnswer.answer is a dictionary with 4 keys:
    facility_location, facility_id, facility_name, facility_sector

    facility_location accepts input in the form
    {
        'lng': <longitude>,
        'lat': <latitude>
    }
    and outputs a GeoJSON.
    """

    __tablename__ = 'answer_facility'
    main_answer = sa.Column(Geometry('POINT', 4326))
    geo_json = column_property(func.ST_AsGeoJSON(main_answer))
    facility_id = sa.Column(pg.TEXT)
    facility_name = sa.Column(pg.TEXT)
    facility_sector = sa.Column(pg.TEXT)

    @hybrid_property
    def answer(self) -> OrderedDict:
        """A dictionary of location, id, name, and sector."""
        return OrderedDict((
            ('facility_location', self.geo_json),
            ('facility_id', self.facility_id),
            ('facility_name', self.facility_name),
            ('facility_sector', self.facility_sector),
        ))

    @answer.setter
    def answer(self, facility_info: dict):
        """Set FacilityAnswer.answer with a dict."""
        self.main_answer = (
            'SRID=4326;POINT({lng} {lat})'
            .format(**facility_info)
        )
        self.facility_id = facility_info['facility_id']
        self.facility_name = facility_info['facility_name']
        self.facility_sector = facility_info['facility_sector']

    __mapper_args__ = {'polymorphic_identity': 'facility'}
    __table_args__ = _answer_mixin_table_args() + (
        sa.CheckConstraint(
            """
            (CASE WHEN (main_answer     IS     NULL) AND
                       (facility_id     IS     NULL) AND
                       (facility_name   IS     NULL) AND
                       (facility_sector IS     NULL)
                THEN 1 ELSE 0 END) +
            (CASE WHEN (main_answer     IS NOT NULL) AND
                       (facility_id     IS NOT NULL) AND
                       (facility_name   IS NOT NULL) AND
                       (facility_sector IS NOT NULL)
                THEN 1 ELSE 0 END) =
            1
            """
        ),
    )


class MultipleChoiceAnswer(_AnswerMixin, Answer):

    """A Choice answer."""

    __tablename__ = 'answer_multiple_choice'
    id = util.pk()
    the_allow_other = sa.Column(sa.Boolean, nullable=False)
    the_allow_dont_know = sa.Column(sa.Boolean, nullable=False)
    main_answer = sa.Column(pg.UUID)
    choice = relationship('Choice')
    answer = synonym('main_answer')
    the_survey_node_id = sa.Column(pg.UUID, nullable=False)
    the_question_id = sa.Column(pg.UUID, nullable=False)
    the_submission_id = sa.Column(pg.UUID, nullable=False)

    __mapper_args__ = {'polymorphic_identity': 'multiple_choice'}
    __table_args__ = _answer_mixin_table_args()[1:] + (
        sa.ForeignKeyConstraint(
            [
                'id',
                'the_allow_other',
                'the_allow_dont_know',
                'the_survey_node_id',
                'the_question_id',
                'the_submission_id',
            ],
            [
                'answer.id',
                'answer.allow_other',
                'answer.allow_dont_know',
                'answer.survey_node_id',
                'answer.question_id',
                'answer.submission_id',
            ]
        ),
        sa.ForeignKeyConstraint(
            ['main_answer', 'the_question_id'],
            ['choice.id', 'choice.question_id']
        ),
        sa.UniqueConstraint(
            'the_survey_node_id', 'main_answer', 'the_submission_id',
            name='cannot_pick_the_same_choice_twice',
        ),
    )


ANSWER_TYPES = {
    'text': TextAnswer,
    'photo': PhotoAnswer,
    'integer': IntegerAnswer,
    'decimal': DecimalAnswer,
    'date': DateAnswer,
    'time': TimeAnswer,
    'timestamp': TimestampAnswer,
    'location': LocationAnswer,
    'facility': FacilityAnswer,
    'multiple_choice': MultipleChoiceAnswer,
}


def construct_answer(*, type_constraint: str, **kwargs) -> Answer:
    """Return a subclass of dokomoforms.models.answer.Answer.

    The subclass is determined by the type_constraint parameter. This utility
    function makes it easy to create an instance of an Answer subclass based
    on external input.

    See http://stackoverflow.com/q/30518484/1475412

    :param type_constraint: the type of the answer. Must be one of the keys of
                            dokomoforms.models.answer.ANSWER_TYPES
    :param kwargs: the keyword arguments to pass to the constructor
    :returns: an instance of one of the Answer subtypes
    :raies: dokomoforms.exc.NotAnAnswerTypeError
    """
    try:
        create_answer = ANSWER_TYPES[type_constraint]
    except KeyError:
        raise NotAnAnswerTypeError(type_constraint)

    return create_answer(**kwargs)
