import os
import pytest
import onegram
import requests

from pathlib import Path
from _pytest.monkeypatch import MonkeyPatch
from betamax import Betamax
from betamax.fixtures.pytest import _casette_name as _cassette_name
from betamax_serializers import pretty_json


@pytest.fixture(scope='session')
def monkeypatch_session():
    mpatch = MonkeyPatch()
    yield mpatch
    mpatch.undo()


@pytest.fixture(scope='session')
def betamax(monkeypatch_session):
    Betamax.register_serializer(pretty_json.PrettyJSONSerializer)
    cassete_dir = Path('tests/cassettes/')
    cassete_dir.mkdir(parents=True, exist_ok=True)
    username = os.environ.get('INSTA_USERNAME')
    password = os.environ.get('INSTA_PASSWORD')
    record_mode = os.environ.get('ONEGRAM_TEST_RECORD_MODE')

    placeholders = [
        {'placeholder': 'INSTA_USERNAME', 'replace': username},
        {'placeholder': 'INSTA_PASSWORD', 'replace': password},
    ]

    options = {
        'serialize_with': 'prettyjson',
        'placeholders': placeholders,
        'record_mode': record_mode,
    }

    with Betamax(requests.Session(),
                 cassette_library_dir=cassete_dir,
                 default_cassette_options=options) as recorder:
        monkeypatch_session.setattr(requests,
                                    'Session',
                                    lambda: recorder.session)
        yield recorder


@pytest.fixture(scope='session', autouse=True)
def session(request, betamax):
    settings = {'RATE_LIMITS': None, 'USER_AGENT': None}
    betamax.use_cassette('fixture_session')
    with onegram.Login(custom_settings=settings) as session:
        betamax.current_cassette.eject()
        yield session


@pytest.fixture(scope='session')
def username():
    username = os.environ.get('ONEGRAM_TEST_USERNAME')
    assert username
    return username


@pytest.fixture(scope='session')
def user(betamax, username):
    betamax.use_cassette('fixture_user')
    try:
        user = onegram.user_info(username)
    finally:
        betamax.current_cassette.eject()
    assert user['id']
    assert user['username'] == username
    return user


@pytest.fixture(scope='session')
def post(betamax, user):
    betamax.use_cassette('fixture_post')
    try:
        post = next(onegram.posts(user))
    finally:
        betamax.current_cassette.eject()
    assert post['id']
    assert post['shortcode']
    assert post['owner']['id'] == user['id']
    return post


@pytest.fixture
def cassette(betamax, request):
    cassette_name = _cassette_name(request, True)
    betamax.use_cassette(cassette_name)
    cassette = betamax.current_cassette
    yield cassette
    cassette.eject()
