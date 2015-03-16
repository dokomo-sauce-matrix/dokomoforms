"""Functions for interacting with surveys."""
from collections import Iterator
import datetime

from sqlalchemy.engine import RowProxy, Connection

from dokomoforms.api import execute_with_exceptions, json_response
from dokomoforms.db import delete_record, update_record, survey_table
from dokomoforms.db.answer import get_answers_for_question, answer_insert, \
    _get_is_other
from dokomoforms.db.answer_choice import get_answer_choices_for_choice_id, \
    answer_choice_insert
from dokomoforms.db.auth_user import get_auth_user_by_email
from dokomoforms.db.question import question_insert, \
    MissingMinimalLogicError, \
    question_select, get_questions_no_credentials
from dokomoforms.db.question_branch import question_branch_insert, \
    MultipleBranchError, get_branches
from dokomoforms.db.question_choice import get_choices, \
    QuestionChoiceDoesNotExistError, RepeatedChoiceError, \
    question_choice_insert
from dokomoforms.db.submission import get_submissions_by_email, \
    submission_insert
from dokomoforms.db.survey import get_free_title, survey_insert, \
    SurveyAlreadyExistsError, survey_select, get_surveys_by_email, display
from dokomoforms.db.type_constraint import TypeConstraintDoesNotExistError


def _determine_choices(connection: Connection,
                       existing_question_id: str,
                       choices: list) -> tuple:
    """
    Pre-process the choices coming from the survey JSON to determine which
    choices to insert and which are updates.

    :param connection: a SQLAlchemy Connection
    :param existing_question_id: the UUID of the existing question (if this is
                                 an update) or None otherwise
    :param choices: the list of choices from the JSON submission
    :return: a tuple of (list of new choices, dictionary of new choice : id of
             old choice)
    :raise RepeatedChoiceError: if a choice is supplied more than once
    :raise QuestionChoiceDoesNotExistError: if an old_choice supplied does not
                                            exist
    """
    # the choices associated with the existing question
    old_choices = []
    if existing_question_id is not None:
        old_choices = get_choices(connection, existing_question_id)
    # a dictionary of choice text : choice id
    old_choice_dict = {ch.choice: ch.question_choice_id for ch in old_choices}
    # the choices to be inserted
    new_choices = []
    # a dictionary of new_choice : choice id
    updates = {}
    old_choice_repeats = set()
    if choices is None:
        return new_choices, updates
    for entry in choices:
        try:
            # choice update
            old_choice = entry['old_choice']
            if old_choice not in old_choice_dict:
                raise QuestionChoiceDoesNotExistError(old_choice)
            if old_choice in old_choice_repeats:
                raise RepeatedChoiceError(entry)
            old_choice_repeats.add(old_choice)
            new_choice = entry['new_choice']
            new_choices.append(new_choice)
            updates[new_choice] = old_choice_dict[old_choice]
        except TypeError:
            # new choice entry
            new_choices.append(entry)
            if entry in old_choice_dict:
                updates[entry] = old_choice_dict[entry]
    new_choice_set = set(new_choices)
    if len(new_choice_set) != len(new_choices):
        raise RepeatedChoiceError(new_choices)
    return new_choices, updates


def _create_choices(connection: Connection,
                    values: dict,
                    question_id: str,
                    submission_map: dict,
                    existing_question_id: str=None) -> Iterator:
    """
    Create the choices of a survey question. If this is an update to an
    existing survey, it will also copy over answers to the questions.

    :param connection: the SQLAlchemy Connection object for the transaction
    :param values: the dictionary of values associated with the question
    :param question_id: the UUID of the question
    :param submission_map: a dictionary mapping old submission_id to new
    :param existing_question_id: the UUID of the existing question (if this is
                                 an update)
    :return: an iterable of the resultant choice fields
    """
    choices = values['choices']
    new_choices, updates = _determine_choices(connection, existing_question_id,
                                              choices)

    for number, choice in enumerate(new_choices):
        choice_dict = {
            'question_id': question_id,
            'survey_id': values['survey_id'],
            'choice': choice,
            'choice_number': number,
            'type_constraint_name': values['type_constraint_name'],
            'question_sequence_number': values['sequence_number'],
            'allow_multiple': values['allow_multiple']}
        executable = question_choice_insert(**choice_dict)
        exc = [('unique_choice_names', RepeatedChoiceError(choice))]
        result = execute_with_exceptions(connection, executable, exc)
        result_ipk = result.inserted_primary_key
        question_choice_id = result_ipk[0]

        if choice in updates:
            question_fields = {'question_id': question_id,
                               'type_constraint_name': result_ipk[2],
                               'sequence_number': result_ipk[3],
                               'allow_multiple': result_ipk[4],
                               'survey_id': values['survey_id']}
            for answer in get_answer_choices_for_choice_id(connection,
                                                           updates[choice]):
                answer_values = question_fields.copy()
                new_submission_id = submission_map[answer.submission_id]
                answer_values['question_choice_id'] = question_choice_id
                answer_values['submission_id'] = new_submission_id
                answer_metadata = answer.answer_choice_metadata
                answer_values['answer_choice_metadata'] = answer_metadata
                connection.execute(answer_choice_insert(**answer_values))

        yield question_choice_id


def _create_questions(connection: Connection,
                      questions: list,
                      survey_id: str,
                      submission_map: dict=None) -> Iterator:
    """
    Create the questions of a survey. If this is an update to an existing
    survey, it will also copy over answers to the questions.

    :param connection: the SQLAlchemy Connection object for the transaction
    :param questions: a list of dictionaries, each containing the values
                      associated with a question
    :param survey_id: the UUID of the survey
    :param submission_map: a dictionary mapping old submission_id to new
    :return: an iterable of the resultant question fields
    """
    for number, question in enumerate(questions, start=1):
        values = question.copy()
        values['sequence_number'] = number
        values['survey_id'] = survey_id

        existing_q_id = values.pop('question_id', None)

        executable = question_insert(**values)
        tcn = values['type_constraint_name']
        exceptions = [('question_type_constraint_name_fkey',
                       TypeConstraintDoesNotExistError(tcn)),
                      ('minimal_logic',
                       MissingMinimalLogicError(values['logic']))]
        result = execute_with_exceptions(connection, executable, exceptions)
        result_ipk = result.inserted_primary_key
        q_id = result_ipk[0]

        choices = list(_create_choices(connection,
                                       values,
                                       q_id,
                                       submission_map=submission_map,
                                       existing_question_id=existing_q_id))

        if existing_q_id is not None:
            question_fields = {'question_id': q_id,
                               'sequence_number': result_ipk[1],
                               'allow_multiple': result_ipk[2],
                               'type_constraint_name': result_ipk[3],
                               'survey_id': survey_id}
            for answer in get_answers_for_question(connection, existing_q_id):
                new_tcn = result_ipk[3]
                old_tcn = question_select(connection,
                                          existing_q_id).type_constraint_name
                if new_tcn != old_tcn:
                    continue
                answer_values = question_fields.copy()
                answer_values['answer_metadata'] = answer.answer_metadata
                new_submission_id = submission_map[answer.submission_id]

                is_other = _get_is_other(answer)
                answer_values['is_other'] = is_other
                if is_other:
                    answer_values['answer'] = answer.answer_text
                else:
                    answer_values['answer'] = answer['answer_' + new_tcn]
                with_other = values['logic']['with_other']

                if new_tcn == 'multiple_choice' and not with_other:
                    continue
                answer_values['submission_id'] = new_submission_id
                connection.execute(answer_insert(**answer_values))

        q_to_seq_number = values['question_to_sequence_number']
        yield {'question_id': q_id,
               'type_constraint_name': tcn,
               'sequence_number': values['sequence_number'],
               'allow_multiple': values['allow_multiple'],
               'choice_ids': choices,
               'question_to_sequence_number': q_to_seq_number}


def _create_branches(connection: Connection,
                     questions_json: list,
                     question_dicts: list,
                     survey_id: str):
    """
    Create the branches in a survey.

    :param connection: the SQLAlchemy Connection object for the transaction
    :param questions_json: a list of dictionaries coming from the JSON input
    :param question_dicts: a list of dictionaries resulting from inserting
                           the questions
    :param survey_id: the UUID of the survey
    """
    for index, question_dict in enumerate(questions_json):
        from_dict = question_dicts[index]
        from_q_id = from_dict['question_id']
        branches = question_dict['branches']
        if branches is None:
            continue
        for branch in branches:
            choice_index = branch['choice_number']
            question_choice_id = from_dict['choice_ids'][choice_index]
            from_tcn = question_dict['type_constraint_name']
            from_mul = from_dict['allow_multiple']
            to_question_index = branch['to_question_number'] - 1
            to_question_id = question_dicts[to_question_index]['question_id']
            to_tcn = question_dicts[to_question_index]['type_constraint_name']
            to_seq = question_dicts[to_question_index]['sequence_number']
            to_mul = question_dicts[to_question_index]['allow_multiple']
            branch_dict = {'question_choice_id': question_choice_id,
                           'from_question_id': from_q_id,
                           'from_type_constraint': from_tcn,
                           'from_sequence_number': index + 1,
                           'from_allow_multiple': from_mul,
                           'from_survey_id': survey_id,
                           'to_question_id': to_question_id,
                           'to_type_constraint': to_tcn,
                           'to_sequence_number': to_seq,
                           'to_allow_multiple': to_mul,
                           'to_survey_id': survey_id}
            executable = question_branch_insert(**branch_dict)
            exc = [('question_branch_from_question_id_question_choice_id_key',
                    MultipleBranchError(question_choice_id))]
            execute_with_exceptions(connection, executable, exc)


def _copy_submission_entries(connection: Connection,
                             existing_survey_id: str,
                             new_survey_id: str,
                             email: str) -> tuple:
    """
    Copy submissions from an existing survey to its updated copy.

    :param connection: the SQLAlchemy connection used for the transaction
    :param existing_survey_id: the UUID of the existing survey
    :param new_survey_id: the UUID of the survey's updated copy
    :param email: the user's e-mail address
    :return: a tuple containing the old and new submission IDs
    """
    for sub in get_submissions_by_email(connection, existing_survey_id,
                                        email=email):
        values = {'submitter': sub.submitter,
                  'submission_time': sub.submission_time,
                  'field_update_time': sub.field_update_time,
                  'survey_id': new_survey_id}
        result = connection.execute(submission_insert(**values))
        yield sub.submission_id, result.inserted_primary_key[0]


def _create_survey(connection: Connection, data: dict) -> str:
    """
    Use the given connection to create a survey within a transaction. If
    this is an update to an existing survey, it will also copy over existing
    submissions.

    :param connection: the SQLAlchemy connection used for the transaction
    :param data: a JSON representation of the survey
    :return: the UUID of the survey in the database
    """
    is_update = 'survey_id' in data

    email = data['email']
    user_id = get_auth_user_by_email(connection, email).auth_user_id
    title = data['survey_title']
    data_q = data['questions']

    # First, create an entry in the survey table
    safe_title = get_free_title(connection, title, user_id)
    survey_values = {'auth_user_id': user_id, 'survey_title': safe_title}
    executable = survey_insert(**survey_values)
    exc = [('survey_title_survey_owner_key',
            SurveyAlreadyExistsError(safe_title))]
    result = execute_with_exceptions(connection, executable, exc)
    survey_id = result.inserted_primary_key[0]

    # a map of old submission_id to new submission_id
    submission_map = None
    if is_update:
        submission_map = {entry[0]: entry[1] for entry in
                          _copy_submission_entries(connection,
                                                   data['survey_id'],
                                                   survey_id,
                                                   data['email'])}

    # Now insert questions.  Inserting branches has to come afterward so
    # that the question_id values actually exist in the tables.
    questions = list(_create_questions(connection, data_q, survey_id,
                                       submission_map=submission_map))
    if -1 not in set(q['question_to_sequence_number'] for q in questions):
        raise SurveyDoesNotEndError()
    _create_branches(connection, data_q, questions, survey_id)

    return survey_id


def create(connection: Connection, data: dict) -> dict:
    """
    Create a survey with questions.

    :param connection: a SQLAlchemy Connection
    :param data: a JSON representation of the survey to be created
    :return: a JSON representation of the created survey
    """
    with connection.begin():
        survey_id = _create_survey(connection, data)

    return get_one(connection, survey_id, email=data['email'])


def _get_choice_fields(choice: RowProxy) -> dict:
    """
    Extract the relevant fields from a record in the question_choice table.

    :param choice: A RowProxy for a record in the question_choice table.
    :return: A dictionary of the fields.
    """
    return {'question_choice_id': choice.question_choice_id,
            'choice': choice.choice,
            'choice_number': choice.choice_number}


def _get_branch_fields(branch: RowProxy) -> dict:
    """
    Extract the relevant fields from a record in the question_branch table.

    :param branch: A RowProxy for a record in the question_branch table.
    :return: A dictionary of the fields.
    """
    return {'question_choice_id': branch.question_choice_id,
            'to_question_id': branch.to_question_id,
            'to_sequence_number': branch.to_sequence_number}


def _get_fields(connection: Connection, question: RowProxy) -> dict:
    """
    Extract the relevant fields from a record in the question table.

    :param connection: a SQLAlchemy Connection
    :param question: A RowProxy for a record in the question table.
    :return: A dictionary of the fields.
    """
    result = {'question_id': question.question_id,
              'question_title': question.question_title,
              'hint': question.hint,
              'sequence_number': question.sequence_number,
              'question_to_sequence_number':
                  question.question_to_sequence_number,
              'allow_multiple': question.allow_multiple,
              'type_constraint_name': question.type_constraint_name,
              'logic': question.logic}
    if question.type_constraint_name == 'multiple_choice':
        choices = get_choices(connection, question.question_id)
        result['choices'] = [_get_choice_fields(choice) for choice in choices]
        branches = get_branches(connection, question.question_id)
        if branches.rowcount > 0:
            result['branches'] = [_get_branch_fields(brn) for brn in branches]
    return result


def _to_json(connection: Connection, survey: RowProxy) -> dict:
    """
    Return the JSON representation of the given survey

    :param connection: a SQLAlchemy Connection
    :param survey: the survey object
    :return: a JSON dict representation
    """
    questions = get_questions_no_credentials(connection, survey.survey_id)
    q_fields = [_get_fields(connection, question) for question in questions]
    return {'survey_id': survey.survey_id,
            'survey_title': survey.survey_title,
            'survey_version': survey.survey_version,
            'survey_metadata': survey.survey_metadata,
            'questions': q_fields,
            'created_on': survey.created_on.isoformat()}


def display_survey(connection: Connection, survey_id: str) -> dict:
    """
    Get a JSON representation of a survey. Use this to display a survey for
    submission purposes.

    :param connection: a SQLAlchemy Connection
    :param survey_id: the UUID of the survey
    :return: the JSON representation.
    """
    return json_response(_to_json(connection, display(connection, survey_id)))


def get_one(connection: Connection,
            survey_id: str,
            auth_user_id: str=None,
            email: str=None) -> dict:
    """
    Get a JSON representation of a survey. You must supply either the
    auth_user_id or the email of the user.

    :param connection: a SQLAlchemy Connection
    :param survey_id: the UUID of the survey
    :param auth_user_id: the UUID of the user
    :param email: the e-mail address of the user
    :return: the JSON representation.
    """
    survey = survey_select(connection, survey_id, auth_user_id=auth_user_id,
                           email=email)
    return json_response(_to_json(connection, survey))


def get_all(connection: Connection, email: str) -> dict:
    """
    Return a JSON representation of all the surveys for a user.

    :param connection: a SQLAlchemy Connection
    :param email: the user's e-mail address.
    :return: the JSON string representation
    """
    surveys = get_surveys_by_email(connection, email)
    return json_response([_to_json(connection, survey) for survey in surveys])


def update(connection: Connection, data: dict):
    """
    Update a survey (title, questions). You can also add or modify questions
    here. Note that this creates a new survey (with new submissions, etc),
    copying everything from the old survey. The old survey's title will be
    changed to end with "(new version created on <time>)".

    :param connection: a SQLAlchemy Connection
    :param data: JSON containing the UUID of the survey and fields to update.
    """
    survey_id = data['survey_id']
    email = data['email']
    existing_survey = survey_select(connection, survey_id, email=email)
    update_time = datetime.datetime.now()

    with connection.begin():
        new_title = '{} (new version created on {})'.format(
            existing_survey.survey_title, update_time.isoformat())
        executable = update_record(survey_table, 'survey_id', survey_id,
                                   survey_title=new_title)
        exc = [('survey_title_survey_owner_key',
                SurveyAlreadyExistsError(new_title))]
        execute_with_exceptions(connection, executable, exc)

        new_survey_id = _create_survey(connection, data)

    return get_one(connection, new_survey_id, email=email)


def delete(connection: Connection, survey_id: str):
    """
    Delete the survey specified by the given survey_id

    :param connection: a SQLAlchemy connection
    :param survey_id: the UUID of the survey
    """
    with connection.begin():
        connection.execute(delete_record(survey_table, 'survey_id', survey_id))
    return json_response('Survey deleted')


class SurveyDoesNotEndError(Exception):
    pass
