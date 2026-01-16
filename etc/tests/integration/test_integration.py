import json
import os
import re
import sys
from http import HTTPStatus
from pathlib import Path
import datetime
import pytest
import requests
import urllib.parse
import pprint
import time
import authx.auth

REPO_DIR = os.path.abspath(f"{os.path.dirname(os.path.realpath(__file__))}/../../..")
sys.path.insert(0, os.path.abspath(f"{REPO_DIR}"))

from settings import get_env
from site_admin_token import get_site_admin_token

ENV = get_env()


class AuthzRequest:
    headers = {}
    method = None
    path = None

    def __init__(self, headers, method, path):
        self.headers = headers
        self.method = method
        self.path = path


# fixtures
@pytest.fixture
def datasets():
    return ["SITE_PM2C~SYNTH_01", "SITE_PM2C~SYNTH_02"]

@pytest.fixture
def user_authz():
    return [
        ("CANDIG_NOT_ADMIN2", "SITE_PM2C~SYNTH_02"),
        ("CANDIG_NOT_ADMIN", "SITE_PM2C~SYNTH_01")
    ]


def user_auth_datasets():
    return [
        ("CANDIG_NOT_ADMIN2", "SITE_PM2C~SYNTH_02"),
        ("CANDIG_NOT_ADMIN", "SITE_PM2C~SYNTH_01"),
        # ("CANDIG_NOT_ADMIN", "TEST_2"),
        ("CANDIG_SITE_ADMIN", "SITE_PM2C~SYNTH_01"),
    ]


## Keycloak tests:


## Does Keycloak respond?
def test_keycloak():
    response = requests.get(
        f"{ENV['KEYCLOAK_PUBLIC_URL']}/auth/realms/{ENV['KEYCLOAK_REALM']}/.well-known/openid-configuration"
    )
    assert response.status_code == 200
    assert "grant_types_supported" in response.json()


## Can we get an access token for a user?
def get_token(username=None, password=None, access_token=False):
    if ENV['CANDIG_ENV']['ENABLE_ROPC'].lower() == "false":
        # ROPC disabled: Makefile should have queried the user
        # and placed the tokens inside tmp/
        with open(f"tmp/pytest-{username}-token", "r") as f:
            refresh_token = f.read()

        if not access_token:
            return refresh_token

        credentials = authx.auth.get_oauth_response(
            keycloak_url=ENV["KEYCLOAK_PUBLIC_URL"],
            client_id=ENV["CANDIG_CLIENT_ID"],
            client_secret=ENV["CANDIG_CLIENT_SECRET"],
            username=username,
            password=password,
            refresh_token=refresh_token
            )
        return credentials["access_token"]
    else:
        payload = {
            "client_id": ENV["CANDIG_CLIENT_ID"],
            "client_secret": ENV["CANDIG_CLIENT_SECRET"],
            "grant_type": "password",
            "username": username,
            "password": password,
            "scope": "openid",
        }
        response = requests.post(
            f"{ENV['KEYCLOAK_PUBLIC_URL']}/auth/realms/{ENV['KEYCLOAK_REALM']}/protocol/openid-connect/token",
            data=payload,
        )
        if response.status_code == 200:
            if access_token:
                return response.json()["access_token"]
            return response.json()["refresh_token"]


def test_get_token():
    assert get_site_admin_token()


## Tyk test: can we get a response from Tyk for all of our services?
def test_tyk():
    modules = ENV['CANDIG_ENV']['CANDIG_MODULES'].split(" ")
    headers = {
        "Authorization": f"Bearer {get_site_admin_token()}"
    }
    endpoints = {
        # all of these endpoints should return JSON
        "htsget": f"{ENV['CANDIG_ENV']['TYK_HTSGET_API_LISTEN_PATH']}/htsget/v1/reads/service-info",
        "drs": f"{ENV['CANDIG_ENV']['TYK_DRS_API_LISTEN_PATH']}/ga4gh/drs/v1/service-info",
        "candig-api": f"{ENV['CANDIG_ENV']['TYK_CANDIG_API_LISTEN_PATH']}/v1/service-info",
        "rnaget": f"{ENV['CANDIG_ENV']['TYK_RNAGET_API_LISTEN_PATH']}/service-info",
        "federation": f"federation/v1/service-info",
        "opa": f"{ENV['CANDIG_ENV']['TYK_OPA_API_LISTEN_PATH']}/v1/data/service/service-info"
    }
    responses = []
    for module in modules:
        if module in endpoints:
            endpoint = endpoints[module]
            response = requests.get(
                f"{ENV['CANDIG_URL']}/{endpoint}", headers=headers, timeout=10
            )
            sc = response.status_code
            try:
                r = response.json()
            except requests.JSONDecodeError as e:
                sc = 500 # to show that the endpoint was not valid json
            responses.append(sc)
            print(f"{endpoint}: {sc == 200}")
    assert all(response == 200 for response in responses)


## Opa tests:
## Test DAC user authorizations

## Can we get the correct dataset response for each user?
def get_omop_datasets(user):
    username = ENV[f"{user}_USER"]
    password = ENV[f"{user}_PASSWORD"]
    token = get_token(username=username, password=password, access_token=True)

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=utf-8"
    }
    request = AuthzRequest(headers, "GET", "/v1/datasets/")
    response = authx.auth.get_opa_datasets(request)

    return response


def add_dataset_authorization(dataset: str, curators: list,
                              team_members: list):
    token = get_site_admin_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=utf-8",
    }

    # create a dataset and its authorizations:
    test_dataset = {
        "dataset_id": dataset,
        "dataset_curators": curators,
        "team_members": team_members
    }

    print(f"{ENV['CANDIG_URL']}/candig-api/v1/authz/dataset")
    response = requests.post(f"{ENV['CANDIG_URL']}/candig-api/v1/authz/dataset", headers=headers, json=test_dataset)
    print(response.text)
    # if the site user is the default user, there should be a warning
    if ENV['CANDIG_SITE_ADMIN_USER'] == ENV['CANDIG_ENV']['DEFAULT_SITE_ADMIN_USER']:
        assert "warnings" in response.json()

    return response.json()


def delete_dataset_authorization(dataset: str):
    token = get_site_admin_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=utf-8",
    }
    response = requests.delete(f"{ENV['CANDIG_URL']}/candig-api/v1/authz/dataset/{dataset}", headers=headers)
    print(response.text)
    return response


## Can we add a dataset authorization and modify it?
@pytest.mark.parametrize("user, dataset", user_auth_datasets())
def test_add_remove_dataset_authorization(user, dataset):
    add_dataset_authorization(dataset, [], [])
    token = get_site_admin_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=utf-8",
    }

    # remove the dataset
    response = delete_dataset_authorization(dataset)
    assert response.status_code == 200

    response = requests.get(f"{ENV['CANDIG_URL']}/candig-api/v1/authz/dataset/{dataset}", headers=headers)
    assert response.status_code == 404


@pytest.mark.parametrize("user, dataset", user_auth_datasets())
def test_user_authorizations(user, dataset):
    # set up these datasets to exist at all:
    add_dataset_authorization(dataset, [], [])

    # remove user from system
    username = ENV[f"{user}_USER"]
    clean_up_user(username)

    # add user to pending users
    safe_name = urllib.parse.quote_plus(username)
    password = ENV[f"{user}_PASSWORD"]
    token = get_token(username=username, password=password)
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=utf-8"
    }

    response = requests.post(
        f"{ENV['CANDIG_URL']}/candig-api/v1/authz/user/pending/request",
        headers=headers
    )
    print(response.text, response.status_code)
    assert response.status_code in [200, 201]
    headers = {
        "Authorization": f"Bearer {get_site_admin_token()}",
        "Content-Type": "application/json; charset=utf-8"
    }
    if response.status_code in [200, 201]:
        # approve user
        response = requests.post(
            f"{ENV['CANDIG_URL']}/candig-api/v1/authz/user/pending/{safe_name}",
            headers=headers
        )
        assert response.status_code == 200
    else:
        # check to see if the user is authorized
        response = requests.get(
            f"{ENV['CANDIG_URL']}/candig-api/v1/authz/user/{safe_name}",
            headers=headers
        )
        assert response.status_code == 200

    # see if user can access dataset before authorizing
    omop_datasets = get_omop_datasets(user)
    assert dataset not in omop_datasets or user == "CANDIG_SITE_ADMIN"

    # add dataset to user's authz
    from datetime import date

    TODAY = date.today()
    THE_FUTURE = str(date(TODAY.year + 1, TODAY.month, TODAY.day))

    response = requests.post(
        f"{ENV['CANDIG_URL']}/candig-api/v1/authz/user/{safe_name}/dac_authorization",
        headers=headers,
        json={"dataset_id": dataset, "start_date": "2000-01-01", "end_date": THE_FUTURE}
    )
    print(response.text)
    assert response.status_code == 200

    # # see if user can access dataset now
    # omop_datasets = get_omop_datasets(user)
    # assert dataset in omop_datasets

    # remove the dataset
    response = requests.delete(
        f"{ENV['CANDIG_URL']}/candig-api/v1/authz/user/{safe_name}/dac_authorization/{dataset}",
        headers=headers
    )
    assert response.status_code == 200


## Is the user a site admin?
def user_admin():
    return [
        ("CANDIG_SITE_ADMIN", True),
        ("CANDIG_NOT_ADMIN", False),
    ]


@pytest.mark.parametrize("user, is_admin", user_admin())
def test_site_admin(user, is_admin):
    payload = {"input": {}}
    username = ENV[f"{user}_USER"]
    password = ENV[f"{user}_PASSWORD"]
    token = get_token(username=username, password=password, access_token=True)

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Bearer {token}"
    }

    request = AuthzRequest(headers, None, None)

    assert authx.auth.is_site_admin(request) == is_admin


def test_add_remove_site_admin():
    token = get_site_admin_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=utf-8",
    }

    # add user1 to site admins
    response = requests.post(
        f"{ENV['CANDIG_URL']}/candig-api/v1/authz/site-role/admin/user_id/{ENV['CANDIG_NOT_ADMIN_USER']}",
        headers=headers
    )
    print(response.text)
    assert response.status_code == 200

    test_site_admin("CANDIG_NOT_ADMIN", True)

    # remove user1 from site admins
    response = requests.delete(
        f"{ENV['CANDIG_URL']}/candig-api/v1/authz/site-role/admin/user_id/{ENV['CANDIG_NOT_ADMIN_USER']}",
        headers=headers
    )
    assert response.status_code == 200
    test_site_admin("CANDIG_NOT_ADMIN", False)


## Vault tests: can we add an aws access key and retrieve it?
# def test_s3_credentials():
#     site_admin_token = get_site_admin_token()
#     headers = {
#         "Authorization": f"Bearer {site_admin_token}",
#         "Content-Type": "application/json; charset=utf-8",
#     }

#     payload = {
#         "endpoint": "https://candig-demo.uhndata.io:9000",
#         "bucket": "test-genomic",
#         "access_key": "vMBfT7WFBLWtrAZaw6K2",
#         "secret_key": "kt2ZKy2BWnDxKCNVhBmkVxd68zv76lKN36yQUjVl"
#     }

#     # set a credential
#     response = requests.post(
#         f"{ENV['CANDIG_URL']}/candig-api/v1/authz/s3-credential", headers=headers, json=payload
#     )
#     # check to see if the error is SSL; if so, try again without https:
#     if "SSLError" in response.text:
#         payload["endpoint"] = "http://candig-demo.uhndata.io:9000"
#         # set a credential
#         response = requests.post(
#             f"{ENV['CANDIG_URL']}/candig-api/v1/authz/s3-credential", headers=headers, json=payload
#         )

#     print(response.text)
#     # make sure that the endpoint was parsed correctly:
#     assert response.json()["endpoint"] == "candig_demo_uhndata_io_9000"

#     # get the credential back
#     url = f"{ENV['CANDIG_URL']}/candig-api/v1/authz/s3-credential/endpoint/{response.json()['endpoint']}/bucket/{response.json()['bucket']}"
#     response = requests.get(url, headers=headers)

#     print(response.text)
#     assert response.json()["access_key"] == payload["access_key"]

#     # delete the credential
#     response = requests.delete(url, headers=headers)

#     print(response.text)
#     assert response.status_code == 204


# =========================|| KATSU TEST BEGIN ||============================= #
# HELPER FUNCTIONS
# -----------------
def clean_up_user(user_name):
    print(f"deleting {user_name}")
    site_admin_token = get_site_admin_token()
    headers = {
        "Authorization": f"Bearer {site_admin_token}",
        "Content-Type": "application/json; charset=utf-8",
    }
    safe_name = urllib.parse.quote_plus(user_name)

    delete_response = requests.delete(
        f"{ENV['CANDIG_URL']}/candig-api/v1/authz/user/{safe_name}",
        headers=headers
    )
    print(f"user delete response status code: {delete_response.status_code}")
    assert (delete_response.status_code == 200 or delete_response.status_code == HTTPStatus.NO_CONTENT or delete_response.status_code == HTTPStatus.NOT_FOUND)


def clean_up_dataset(test_id):
    """
    Deletes a dataset and all related objects in omop, htsget and opa. Expected either
    successful delete or not found if the datasets are not ingested.
    """
    print(f"deleting {test_id}")
    site_admin_token = get_site_admin_token()
    headers = {
        "Authorization": f"Bearer {site_admin_token}",
        "Content-Type": "application/json; charset=utf-8",
    }

    # delete dataset
    delete_response = requests.delete(f"{ENV['CANDIG_URL']}/candig-api/v1/datasets/{test_id}",
                                      headers=headers)
    print(f"dataset delete response status code: {delete_response.status_code} {delete_response.text}")
    assert (delete_response.status_code == 200 or delete_response.status_code == HTTPStatus.NO_CONTENT or delete_response.status_code == HTTPStatus.NOT_FOUND)


# def clean_up_program_htsget(program_id):
    # site_admin_token = get_site_admin_token()
    # headers = {
    #     "Authorization": f"Bearer {site_admin_token}",
    #     "Content-Type": "application/json; charset=utf-8",
    # }
    # delete_response = requests.delete(
    #     f"{ENV['CANDIG_URL']}/genomics/ga4gh/drs/v1/programs/{program_id}",
    #     headers=headers
    # )
    # print(delete_response.text)
    # assert delete_response.status_code == 200


def test_ingest_not_admin_omop(datasets, user_authz):
    """Test ingest of SYNTH_01 as CANDIG_NOT_ADMIN_USER, without and with program authorization."""

    token = get_token(
        username=ENV["CANDIG_NOT_ADMIN2_USER"],
        password=ENV["CANDIG_NOT_ADMIN2_PASSWORD"],
    )
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=utf-8",
    }
    query_response = requests.get(
        f"{ENV['CANDIG_URL']}/candig-api/v1/datasets/statistics", headers=headers)
    if query_response.status_code == 200:
        print(query_response.text)
        query_datasets = list(query_response.json()['persons_per_dataset'].keys())
        for dataset in query_datasets:
            if dataset in datasets:
                print(f"cleaning up {dataset}")
                clean_up_dataset(dataset)

    token = get_token(
        username=ENV["CANDIG_NOT_ADMIN_USER"],
        password=ENV["CANDIG_NOT_ADMIN_PASSWORD"],
    )
    headers = {
        "Authorization": f"Bearer {token}"
    }
    with open("etc/tests/integration/omop-sample.json", "rb") as f:
        files = {"file": ("etc/tests/integration/omop-sample.json", f, "application/json")}
        response = requests.post(f"{ENV['CANDIG_URL']}/candig-api/v1/datasets/upload", headers=headers, files=files)
        # when the user has no admin access, they should not be allowed
        assert response.status_code == 403

    # add dataset authorization
    for dataset in datasets:
        add_dataset_authorization(dataset, curators=[ENV["CANDIG_NOT_ADMIN_USER"]], team_members=[])

    token = get_token(
        username=ENV["CANDIG_NOT_ADMIN_USER"],
        password=ENV["CANDIG_NOT_ADMIN_PASSWORD"],
    )
    headers = {
        "Authorization": f"Bearer {token}"
    }
    # When dataset authorization is added, ingest should be allowed
    headers = {
        "Authorization": f"Bearer {token}"
    }
    with open("etc/tests/integration/omop-sample.json", "rb") as f:
        files = {"file": ("etc/tests/integration/omop-sample.json", f, "application/json")}
        response = requests.post(f"{ENV['CANDIG_URL']}/candig-api/v1/datasets/upload", headers=headers, files=files)

    try:
        queue_id = response.json()["queue_id"]
    except Exception as e:
        print(response.json())
        assert False

    response = requests.get(f"{ENV['CANDIG_URL']}/candig-api/v1/datasets/upload/status/{queue_id}", headers=headers)
    while response.status_code == 200 and response.json()["status"] == "In Queue":
        time.sleep(2)
        response = requests.get(f"{ENV['CANDIG_URL']}/candig-api/v1/datasets/upload/status/{queue_id}", headers=headers)
    print(response.text)
    assert response.json()["errors"] is None
    assert response.json()["ingested_count"] == 12
    omop_response = requests.get(f"{ENV['CANDIG_URL']}/candig-api/v1/datasets/statistics")
    if omop_response.status_code == 200:
        omop_datasets = [x['dataset_id'] for x in omop_response.json()]
        print(f"Currently ingested omop datasets: {omop_datasets}")
        assert datasets[0] in omop_datasets
    else:
        print(f"Looks like ingest failed with status code: {omop_response.status_code}")



def test_ingest_admin_omop(datasets, user_authz):
    """Test whether an admin can ingest each of the synthetic data datasets can be ingested and add the expected
    dataset authorizations."""
    token = get_token(
        username=ENV["CANDIG_NOT_ADMIN2_USER"],
        password=ENV["CANDIG_NOT_ADMIN2_PASSWORD"],
    )
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=utf-8",
    }
    query_response = requests.get(
        f"{ENV['CANDIG_URL']}/candig-api/v1/datasets/statistics", headers=headers)
    if query_response.status_code == 200:
        query_datasets = list(query_response.json()['persons_per_dataset'].keys())
        for dataset in query_datasets:
            if dataset in datasets:
                print(f"cleaning up {dataset}")
                clean_up_dataset(dataset)

    token = get_site_admin_token()
    headers = {
        "Authorization": f"Bearer {token}"
    }
    with open("etc/tests/integration/omop-sample.json", "rb") as f:
        files = {"file": ("etc/tests/integration/omop-sample.json", f, "application/json")}
        response = requests.post(f"{ENV['CANDIG_URL']}/candig-api/v1/datasets/upload", headers=headers, files=files)

    # no dataset auth: should fail
    print(response.text)
    assert response.status_code != 200

    for dataset in datasets:
        add_dataset_authorization(dataset, [], team_members=[])

    print(f"Sending {datasets} clinical data to candig-api...")
    with open("etc/tests/integration/omop-sample.json", "rb") as f:
        files = {"file": ("etc/tests/integration/omop-sample.json", f, "application/json")}
        response = requests.post(f"{ENV['CANDIG_URL']}/candig-api/v1/datasets/upload", headers=headers, files=files)
        print(f"Ingest response code: {response.status_code}")

    try:
        queue_id = response.json()["queue_id"]
    except KeyError as e:
        print("Ingest was not successful, `queue_id` not found in response, see error messages below")
        print(response.json())

    response = requests.get(f"{ENV['CANDIG_URL']}/candig-api/v1/datasets/upload/status/{queue_id}", headers=headers)
    while response.status_code == 200 and response.json()["status"] == "In Queue":
        time.sleep(2)
        response = requests.get(f"{ENV['CANDIG_URL']}/candig-api/v1/datasets/upload/status/{queue_id}", headers=headers)
    print(response.json())
    assert response.json()["errors"] is None
    assert response.json()["ingested_count"] == 12
    omop_response = requests.get(f"{ENV['CANDIG_URL']}/candig-api/v1/datasets/statistics")
    if omop_response.status_code == 200:
        omop_datasets = [x['dataset_id'] for x in omop_response.json()]
        print(f"Currently ingested omop datasets: {omop_datasets}")
        assert dataset in omop_datasets
    else:
        print(f"Looks like ingest failed with status code: {omop_response.status_code}")
    # Reinstate expected dataset authorizations
    for user, dataset in user_authz:
        add_dataset_authorization(dataset, curators=[ENV[f"{user}_USER"]], team_members=[f"{user}_USER"])


## Htsget tests:

# def test_ingest_not_admin_htsget():
    # with open("lib/candig-ingest/candigv2-ingest/tests/small_dataset_genomic_ingest.json", 'r') as f:
    #     test_data = json.load(f)
#
    # token = get_token(
    #     username=ENV["CANDIG_NOT_ADMIN_USER"],
    #     password=ENV["CANDIG_NOT_ADMIN_PASSWORD"],
    # )
    # headers = {
    #     "Authorization": f"Bearer {token}",
    #     "Content-Type": "application/json; charset=utf-8",
    # }
    # response = requests.post(f"{ENV['CANDIG_URL']}/candig-api/v1/datasets/upload", headers=headers, json=test_data)
    # # when the user has no admin access, they should not be allowed
    # assert response.status_code == 400
#
    # add_dataset_authorization(f"{ENV['CANDIG_ENV']['CANDIG_SITE_LOCATION']}-SYNTH_01", [ENV['CANDIG_NOT_ADMIN_USER']], team_members=[ENV['CANDIG_NOT_ADMIN_USER']])
    # add_dataset_authorization(f"{ENV['CANDIG_ENV']['CANDIG_SITE_LOCATION']}-SYNTH_02", [ENV['CANDIG_NOT_ADMIN_USER']], team_members=[ENV['CANDIG_NOT_ADMIN_USER']])
    # token = get_token(
    #     username=ENV["CANDIG_NOT_ADMIN_USER"],
    #     password=ENV["CANDIG_NOT_ADMIN_PASSWORD"],
    # )
    # headers = {
    #     "Authorization": f"Bearer {token}",
    #     "Content-Type": "application/json; charset=utf-8",
    # }
    # # since we're only ingesting for a quick test before we delete again, don't bother indexing
    # response = requests.post(f"{ENV['CANDIG_URL']}/candig-api/v1/datasets/upload", headers=headers, json=test_data, params={"do_not_index": True})
    # try:
    #     queue_id = response.json()["queue_id"]
    # except Exception as e:
    #     print(f"Ingest was not successful: {type(e)} {str(e)}")
    #     print(response.json())
    #     assert False
    # response = requests.get(f"{ENV['CANDIG_URL']}/candig-api/v1/datasets/upload/status/{queue_id}", headers=headers)
    # while response.status_code == 200:
    #     time.sleep(2)
    #     response = requests.get(f"{ENV['CANDIG_URL']}/candig-api/v1/datasets/upload/status/{queue_id}", headers=headers)
#
    # # when the user has dataset_curator role, they should be allowed
    # assert response.status_code == 201
    # for dataset in response.json():
    #     results = response.json()[dataset]
    #     print(json.dumps(results["results"], indent=2))
    #     for res in results["results"]:
    #         assert "error processing" not in res
    # # clean up before the next test
    # datasets=["SYNTH_01", "SYNTH_02", "SYNTH_03", "SYNTH_04"]
    # datasets = [ENV['CANDIG_ENV']['CANDIG_SITE_LOCATION']+ "-" + p for p in datasets]
    # for dataset in datasets:
    #     clean_up_dataset_htsget(dataset)
    # add_dataset_authorization(f"{ENV['CANDIG_ENV']['CANDIG_SITE_LOCATION']}-SYNTH_01", [ENV['CANDIG_NOT_ADMIN_USER']], team_members=[ENV['CANDIG_NOT_ADMIN_USER']])
    # add_dataset_authorization(f"{ENV['CANDIG_ENV']['CANDIG_SITE_LOCATION']}-SYNTH_02", [ENV['CANDIG_NOT_ADMIN2_USER']], team_members=[ENV['CANDIG_NOT_ADMIN2_USER']])
#
#
#
# def test_ingest_admin_htsget():
    # with open("lib/candig-ingest/candigv2-ingest/tests/small_dataset_genomic_ingest.json", 'r') as f:
    #     test_data = json.load(f)
#
    # token = get_site_admin_token()
    # headers = {
    #     "Authorization": f"Bearer {token}",
    #     "Content-Type": "application/json; charset=utf-8",
    # }
    # response = requests.post(f"{ENV['CANDIG_URL']}/candig-api/v1/datasets/upload", headers=headers, json=test_data)
    # try:
    #     queue_id = response.json()["queue_id"]
    # except Exception as e:
    #     print(f"Ingest was not successful: {type(e)} {str(e)}")
    #     print(response.json())
    #     assert False
    # response = requests.get(f"{ENV['CANDIG_URL']}/candig-api/v1/datasets/upload/status/{queue_id}", headers=headers)
    # while response.status_code == 200:
    #     time.sleep(2)
    #     response = requests.get(f"{ENV['CANDIG_URL']}/candig-api/v1/datasets/upload/status/{queue_id}", headers=headers)
    # # when the user has admin access, they should be allowed
    # assert response.status_code == 201
    # for dataset in response.json():
    #     results = response.json()[dataset]
    #     print(json.dumps(results["results"], indent=2))
    #     for res in results["results"]:
    #         assert "error processing" not in res


## Can we access the data when authorized to do so?
def user_access():
    return [
        (
            "CANDIG_NOT_ADMIN_USER",
            "CANDIG_NOT_ADMIN_PASSWORD",
            f"{ENV["CANDIG_ENV"]["CANDIG_SITE_LOCATION"]}-NA18537-vcf",
            False,
        ),  # user1 cannot access NA18537 as part of SYNTH_02
        (
            "CANDIG_NOT_ADMIN_USER",
            "CANDIG_NOT_ADMIN_PASSWORD",
            f"{ENV["CANDIG_ENV"]["CANDIG_SITE_LOCATION"]}-test",
            True,
        ),  # user1 can access test as part of SYNTH_01
        (
            "CANDIG_NOT_ADMIN2_USER",
            "CANDIG_NOT_ADMIN2_PASSWORD",
            f"{ENV["CANDIG_ENV"]["CANDIG_SITE_LOCATION"]}-NA02102-bam",
            False
        ),  # user2 cannot access NA02102-bam
        (
            "CANDIG_NOT_ADMIN2_USER",
            "CANDIG_NOT_ADMIN2_PASSWORD",
            f"{ENV["CANDIG_ENV"]["CANDIG_SITE_LOCATION"]}-multisample_1",
            True
        )  # user2 can access multisample_1
    ]


# @pytest.mark.parametrize("user, password, obj, access", user_access())
# def test_htsget_access_data(user, password, obj, access):
    # username = ENV[user]
    # password = ENV[password]
    # headers = {
    #     "Authorization": f"Bearer {get_token(username=username, password=password)}",
    #     "Content-Type": "application/json; charset=utf-8",
    # }
    # params = {"class": "header"}
    # response = requests.get(
    #     f"{ENV['CANDIG_URL']}/genomics/htsget/v1/variants/data/{obj}",
    #     headers=headers,
    #     params=params,
    # )
    # print(f"\n{ENV['CANDIG_URL']}/genomics/htsget/v1/variants/data/{obj}\n")
    # assert (response.status_code == 200) == access
#
#
# def test_experiment_metadata():
    # username = ENV["CANDIG_NOT_ADMIN2_USER"]
    # password = ENV["CANDIG_NOT_ADMIN2_PASSWORD"]
    # headers = {
    #     "Authorization": f"Bearer {get_token(username=username, password=password)}",
    #     "Content-Type": "application/json; charset=utf-8",
    # }
    # response = requests.get(f"{ENV['CANDIG_URL']}/genomics/htsget/v1/experiments/{ENV["CANDIG_ENV"]["CANDIG_SITE_LOCATION"]}-SEQ_NULL_0001", headers=headers)
    # assert "genomes" in response.json()
    # # the experiment is what is listed in the genomes as wgs
    # assert f"{ENV["CANDIG_ENV"]["CANDIG_SITE_LOCATION"]}-SEQ_NULL_0001" in response.json()["genomes"]
    # response = requests.get(f"{ENV['CANDIG_URL']}/genomics/htsget/v1/experiments/{ENV["CANDIG_ENV"]["CANDIG_SITE_LOCATION"]}-SEQ_0072", headers=headers)
    # assert "genomes" in response.json()
    # assert f"{ENV["CANDIG_ENV"]["CANDIG_SITE_LOCATION"]}-SEQ_0072" in response.json()["genomes"]
    # response = requests.get(f"{ENV['CANDIG_URL']}/genomics/htsget/v1/experiments/{ENV["CANDIG_ENV"]["CANDIG_SITE_LOCATION"]}-SEQ_ALL_0002", headers=headers)
    # assert "genomes" in response.json()
    # pprint.pprint(response.json())
    # assert f"{ENV["CANDIG_ENV"]["CANDIG_SITE_LOCATION"]}-SEQ_ALL_0002" in response.json()["genomes"]
#
#
# def test_ingest_rnaget():
    # token = get_site_admin_token()
    # headers = {
    #     "Authorization": f"Bearer {token}",
    #     "Content-Type": "application/json; charset=utf-8",
    # }
    # response = requests.get(f"{ENV['CANDIG_URL']}/genomics/ga4gh/drs/v1/objects/{ENV["CANDIG_ENV"]["CANDIG_SITE_LOCATION"]}-NA18537-counts", headers=headers)
    # assert response.status_code == 200
#
    # assert "metadata" in response.json()
    # assert "analysis_type" in response.json()["metadata"] and response.json()["metadata"]["analysis_type"] == "sequence_annotation"
    # assert "analysis_attribute" in response.json()["metadata"]
    # assert "subtype" in response.json()["metadata"]["analysis_attribute"] and response.json()["metadata"]["analysis_attribute"]["subtype"] == "expression_count"
#
    # query = {
    #   "genes": [
    #     "ENSG00000000003.15"
    #   ],
    #   "method": "tpm"
    # }
    # response = requests.post(f"{ENV['CANDIG_URL']}/rnaget/expressions", json=query, headers=headers)
    # assert response.status_code == 200
    # assert len(response.json()["expressions"]) > 0
#
#
# def test_index_success():
    # # wait to make sure that the final vcf, NA18537.vcf.gz, has been indexed
    # token = get_site_admin_token()
    # headers = {
    #     "Authorization": f"Bearer {token}",
    #     "Content-Type": "application/json; charset=utf-8",
    # }
    # response = requests.get(f"{ENV['CANDIG_URL']}/genomics/ga4gh/drs/v1/objects/{ENV["CANDIG_ENV"]["CANDIG_SITE_LOCATION"]}-NA18537-vcf", headers=headers)
    # tries = 0
    # print(response.json())
    # while response.status_code != 200 or "indexed" not in response.json() or response.json()['indexed'] != 1:
    #     time.sleep(2)
    #     response = requests.get(f"{ENV['CANDIG_URL']}/genomics/ga4gh/drs/v1/objects/{ENV["CANDIG_ENV"]["CANDIG_SITE_LOCATION"]}-NA18537-vcf", headers=headers)
    #     print(response.json())
    #     tries = tries + 1
    #     if tries > 120:
    #         print("indexing is taking too long")
    #         assert False
    # token = get_token(
    #     username=ENV["CANDIG_NOT_ADMIN_USER"],
    #     password=ENV["CANDIG_NOT_ADMIN_PASSWORD"],
    # )
    # headers = {
    #     "Authorization": f"Bearer {token}",
    #     "Content-Type": "application/json; charset=utf-8",
    # }
    # response = requests.get(f"{ENV['CANDIG_URL']}/genomics/ga4gh/drs/v1/objects/{ENV["CANDIG_ENV"]["CANDIG_SITE_LOCATION"]}-test", headers=headers)
    # assert "indexed" in response.json()
    # print(response.json())
    # assert response.json()['indexed'] == 1
#
    # token = get_token(
    #     username=ENV["CANDIG_NOT_ADMIN2_USER"],
    #     password=ENV["CANDIG_NOT_ADMIN2_PASSWORD"],
    # )
    # headers = {
    #     "Authorization": f"Bearer {token}",
    #     "Content-Type": "application/json; charset=utf-8",
    # }
    # response = requests.get(f"{ENV['CANDIG_URL']}/genomics/ga4gh/drs/v1/objects/{ENV["CANDIG_ENV"]["CANDIG_SITE_LOCATION"]}-multisample_1", headers=headers)
    # assert "indexed" in response.json()
    # print(response.json())
    # assert response.json()['indexed'] == 1
#
#
# ## Does Beacon return the correct level of authorized results?
# def beacon_access():
    # return [
    #     (
    #         "CANDIG_NOT_ADMIN_USER",
    #         "CANDIG_NOT_ADMIN_PASSWORD",
    #         "NC_000021.9:g.5030847T>A", # chr21	5030847	.	T	A
    #         [f"{ENV['CANDIG_ENV']['CANDIG_SITE_LOCATION']}-SYNTH_01"],
    #         [f"{ENV['CANDIG_ENV']['CANDIG_SITE_LOCATION']}-SYNTH_02"],
    #     ),
    #     (   # user2 can access NA18537-vcf, multisample_1, HG02102
    #         "CANDIG_NOT_ADMIN2_USER",
    #         "CANDIG_NOT_ADMIN2_PASSWORD",
    #         "NC_000021.9:g.5030847T>A", # chr21	5030847	.	T	A
    #         [f"{ENV['CANDIG_ENV']['CANDIG_SITE_LOCATION']}-SYNTH_02"],
    #         [],
    #     )
    # ]
#
#
# @pytest.mark.parametrize("user, password, search, can_access, cannot_access", beacon_access())
# def test_beacon(user, password, search, can_access, cannot_access):
    # username = ENV[user]
    # password = ENV[password]
    # headers = {
    #     "Authorization": f"Bearer {get_token(username=username, password=password)}",
    #     "Content-Type": "application/json; charset=utf-8",
    # }
    # params = {"allele": search}
    # response = requests.get(
    #     f"{ENV['CANDIG_URL']}/genomics/beacon/v2/g_variants",
    #     headers=headers,
    #     params=params,
    # )
    # pprint.pprint(response.json())
    # print(can_access)
    # print(cannot_access)
    # for c in can_access:
    #     assert c in str(response.json())
    # for c in cannot_access:
    #     assert c not in str(response.json())
    # # print(response.json())
#
#
# def verify_samples():
    # return [
    #     (
    #         f"{ENV["CANDIG_ENV"]["CANDIG_SITE_LOCATION"]}-multisample_1",
    #         "multisample_1.vcf.gz",
    #         "CANDIG_NOT_ADMIN2_USER",
    #         "CANDIG_NOT_ADMIN2_PASSWORD"
    #     ),
    #     (
    #         f"{ENV["CANDIG_ENV"]["CANDIG_SITE_LOCATION"]}-NA02102-bam",
    #         "NA02102.bam",
    #         "CANDIG_NOT_ADMIN_USER",
    #         "CANDIG_NOT_ADMIN_PASSWORD"
    #     )
    # ]
#
#
# @pytest.mark.parametrize("object_id, file_name, user, password", verify_samples())
# def test_verify_htsget(object_id, file_name, user, password):
    # token = get_token(
    #     username=ENV[user],
    #     password=ENV[password],
    # )
#
    # headers = {
    #     "Authorization": f"Bearer {token}",
    #     "Content-Type": "application/json; charset=utf-8",
    # }
    # # get a GenomicDataDrsObject
    # response = requests.get(f"{ENV['CANDIG_URL']}/genomics/ga4gh/drs/v1/objects/{file_name}", headers=headers)
    # assert response.status_code == 200
    # new_json = response.json()
#
    # # mess up its access_url
    # old_url = new_json["access_methods"][0]["access_url"]["url"]
    # new_json["access_methods"][0]["access_url"]["url"] += "test"
#
    # post_token = get_site_admin_token()
    # post_headers = {
    #     "Authorization": f"Bearer {post_token}",
    #     "Content-Type": "application/json; charset=utf-8",
    # }
#
    # response = requests.post(f"{ENV['CANDIG_URL']}/genomics/ga4gh/drs/v1/objects", headers=post_headers, json=new_json)
#
    # # verification should give us a False result
    # response = requests.get(f"{ENV['CANDIG_URL']}/genomics/htsget/v1/{object_id}/verify", headers=headers)
    # assert response.status_code == 200
    # assert response.json()["result"] == False
#
    # # fix it back
    # new_json["access_methods"][0]["access_url"]["url"] = old_url
    # response = requests.post(f"{ENV['CANDIG_URL']}/genomics/ga4gh/drs/v1/objects", headers=post_headers, json=new_json)
#
    # # verification should give us a True result
    # response = requests.get(f"{ENV['CANDIG_URL']}/genomics/htsget/v1/{object_id}/verify", headers=headers)
    # assert response.status_code == 200
    # assert response.json()["result"] == True
#
#
# def test_program_status():
    # token = get_site_admin_token()
    # headers = {
    #     "Authorization": f"Bearer {token}",
    #     "Content-Type": "application/json; charset=utf-8",
    # }
    # response = requests.get(f"{ENV['CANDIG_URL']}/genomics/ga4gh/drs/v1/programs/{ENV['CANDIG_ENV']['CANDIG_SITE_LOCATION']}-SYNTH_02/status", headers=headers)
    # assert "index_complete" in response.json()
    # assert len(response.json()['index_complete']) > 0


## Federation tests:

# Do we have at least one server present?
def test_server_count():
    token = get_token(
        username=ENV["CANDIG_NOT_ADMIN_USER"], password=ENV["CANDIG_NOT_ADMIN_PASSWORD"]
    )
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=utf-8",
    }
    response = requests.get(
        f"{ENV['CANDIG_URL']}/federation/v1/servers", headers=headers
    )
    print(response.json())
    assert len(response.json()) > 0


# Do we have at least one service present?
def test_services_count():
    token = get_token(
        username=ENV["CANDIG_NOT_ADMIN_USER"], password=ENV["CANDIG_NOT_ADMIN_PASSWORD"]
    )
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=utf-8",
    }
    response = requests.get(
        f"{ENV['CANDIG_URL']}/federation/v1/services", headers=headers
    )
    print(response.json())
    assert len(response.json()) > 0
    services = map(lambda x: x["id"], response.json())
    assert "htsget" in services


# Do federated and non-federated calls look correct?
def test_federation_call():
    body = {
        "service": "candig-api",
        "method": "GET",
        "payload": {},
        "path": "v1/service-info",
    }

    token = get_site_admin_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "content-type": "application/json",
        "federation": "false",
    }

    response = requests.post(
        f"{ENV['CANDIG_URL']}/federation/v1/fanout", headers=headers, json=body
    )
    print(response.json())
    assert "results" in response.json()

    headers["federation"] = "true"
    response = requests.post(
        f"{ENV['CANDIG_URL']}/federation/v1/fanout", headers=headers, json=body
    )
    print(response.json())
    assert "list" in str(type(response.json()))
    assert "results" in response.json()[0]


# # Query Test: Get all donors
# def test_query_donors_all():
#     token = get_token(username=ENV['CANDIG_NOT_ADMIN2_USER'],
#                       password=ENV['CANDIG_NOT_ADMIN2_PASSWORD'])
#     headers = {
#         "Authorization": f"Bearer {token}",
#         "Content-Type": "application/json; charset=utf-8",
#     }
#
#     params = {}
#     response = requests.get(
#         f"{ENV['CANDIG_URL']}/query/query", headers=headers, params=params
#     ).json()
#     print(response)
#
#     # CANDIG_NOT_ADMIN2_USER has authorization for SYNTH_02, so expects a return of 10 donors which is the first page of results
#     if len(response["results"]) != 10:
#         returned_donors = [x['program_id'] + ": " + (x['submitter_donor_id']) for x in response['results']]
#         print(f"Expected to get 10 donors returned but query returned {len(response["results"])}.")
#         print(f"Donors returned were: \n{"\n".join(returned_donors)}")
#     assert response and len(response["results"]) == 10
#
#     # Check the summary stats as well
#     summary_stats = response["summary"]
#     pprint.pprint(summary_stats)
#
#     expected_response = {
#         'age_at_diagnosis': {
#             '30-39 Years': 1,
#             '40-49 Years': 8,
#             '50-59 Years': 8
#         },
#         'primary_site_count': {
#             'Breast': 4,
#             'Bronchus and lung': 4,
#             'Colon': 4,
#             'None': 4,
#             'Skin': 4
#         },
#         'patients_per_program': {
#             f'{ENV['CANDIG_ENV']['CANDIG_SITE_LOCATION']}-SYNTH_02': 20
#         },
#         'treatment_type_count': {
#             'Bone marrow transplant': 7,
#             'Other': 9,
#             'Photodynamic therapy': 9,
#             'Radiation therapy': 16,
#             'Stem cell transplant': 9,
#             'Surgery': 23,
#             'Systemic therapy': 40,
#             'Targeted molecular therapy': 7
#         }
#     }
#     for category in expected_response.keys():
#         for value in expected_response[category].keys():
#             if summary_stats[category][value] != expected_response[category][value]:
#                 print(f"\n\nExpected value for {category}: {value} was {expected_response[category][value]} but query returned {summary_stats[category][value]}\n")
#                 print("Check the returned summary stats below against the expected response:")
#                 pprint.pprint(summary_stats)
#             assert summary_stats[category][value] == expected_response[category][value]
#
# # Test 2: Search for a specific donor
# def test_query_donor_search():
#     token = get_token(username=ENV['CANDIG_NOT_ADMIN2_USER'],
#                       password=ENV['CANDIG_NOT_ADMIN2_PASSWORD'])
#     headers = {
#         "Authorization": f"Bearer {token}",
#         "Content-Type": "application/json; charset=utf-8",
#     }
#
#     params = {
#         "treatment": "Radiation therapy"
#     }
#     response = requests.get(
#         f"{ENV['CANDIG_URL']}/query/query", headers=headers, params=params
#     ).json()
#     pprint.pprint(response)
#     assert response and len(response["results"]) == 10
#
#     # Check the summary stats as well
#     summary_stats = response["summary"]
#     pprint.pprint(summary_stats)
#     expected_response = {
#         'age_at_diagnosis': {
#             '30-39 Years': 1,
#             '40-49 Years': 6,
#             '50-59 Years': 6
#         },
#         'primary_site_count': {
#             'Breast': 3,
#             'Bronchus and lung': 3,
#             'Colon': 3,
#             'None': 3,
#             'Skin': 3
#         },
#         'patients_per_program': {
#             f'{ENV['CANDIG_ENV']['CANDIG_SITE_LOCATION']}-SYNTH_02': 15
#         },
#         'treatment_type_count': {
#             'Bone marrow transplant': 6,
#             'Other': 8,
#             'Photodynamic therapy': 8,
#             'Radiation therapy': 16,
#             'Stem cell transplant': 7,
#             'Surgery': 18,
#             'Systemic therapy': 30,
#             'Targeted molecular therapy': 7}
#     }
#     for category in expected_response.keys():
#         for value in expected_response[category].keys():
#             if summary_stats[category][value] != expected_response[category][value]:
#                 print(f"\n\nExpected value for {category}: {value} was {expected_response[category][value]} but query returned {summary_stats[category][value]}\n")
#                 print("Check the returned summary stats below against expected response:")
#                 pprint.pprint(summary_stats)
#             assert summary_stats[category][value] == expected_response[category][value]
#
#
# # Can we can find donors by querying a specific region of the genome?
# def test_query_genomic():
#     # tests that a request sent via query to htsget-beacon properly prunes the data
#     token = get_token(username=ENV['CANDIG_NOT_ADMIN2_USER'],
#                       password=ENV['CANDIG_NOT_ADMIN2_PASSWORD'])
#     headers = {
#         "Authorization": f"Bearer {token}",
#         "Content-Type": "application/json; charset=utf-8",
#     }
#     # look for something that is in multisample_1
#     params = {
#         "chrom": "chr21:5030000-5030847",
#         "assembly": "hg38"
#     }
#     response = requests.get(
#         f"{ENV['CANDIG_URL']}/query/query", headers=headers, params=params
#     )
#     if len(response.json()["results"]) != 1:
#         print(f"\n\nExpected 1 result from the genomic query using position 'chr21:5030000-5030847' but got {len(response.json()["results"])}")
#         if len(response.json()["results"]) > 0:
#             print("Got results from:")
#             for donor in response.json()["results"]:
#                 print(f"{donor["program_id"]}: {donor["submitter_donor_id"]}")
#     assert response and len(response.json()["results"]) == 1
#     assert response.json()["results"][0]['program_id'] == f"{ENV['CANDIG_ENV']['CANDIG_SITE_LOCATION']}-SYNTH_02"
#     assert response.json()["results"][0]['submitter_donor_id'] == f"{ENV['CANDIG_ENV']['CANDIG_SITE_LOCATION']}-DONOR_0021"
#
#     token = get_token(username=ENV['CANDIG_NOT_ADMIN_USER'],
#                       password=ENV['CANDIG_NOT_ADMIN_PASSWORD'])
#     headers = {
#         "Authorization": f"Bearer {token}",
#         "Content-Type": "application/json; charset=utf-8",
#     }
#     # look for something that is in multisample_2
#     params = {
#         "gene": "LOC102723996",
#         "assembly": "hg38"
#     }
#     response = requests.get(
#         f"{ENV['CANDIG_URL']}/query/query", headers=headers, params=params
#     )
#
#     if len(response.json()["results"]) != 1:
#         print(f"\n\nExpected 1 result from the genomic query using gene name 'LOC102723996' but got {len(response.json()["results"])}")
#         if len(response.json()["results"]) > 0:
#             print("Got results from:")
#             for donor in response.json()["results"]:
#                 print(f"{donor["program_id"]}: {donor["submitter_donor_id"]}")
#     assert response and len(response.json()["results"]) == 1
#     assert response.json()["results"][0]['program_id'] == f"{ENV['CANDIG_ENV']['CANDIG_SITE_LOCATION']}-SYNTH_01"
#     assert response.json()["results"][0]['submitter_donor_id'] == f"{ENV['CANDIG_ENV']['CANDIG_SITE_LOCATION']}-DONOR_NULL_0001"
#
#     token = get_token(username=ENV['CANDIG_NOT_ADMIN_USER'],
#                       password=ENV['CANDIG_NOT_ADMIN_PASSWORD'])
#     headers = {
#         "Authorization": f"Bearer {token}",
#         "Content-Type": "application/json; charset=utf-8",
#     }
#     # look for something that is in NA20787
#     params = {
#         "gene": "TPTE",
#         "assembly": "hg38"
#     }
#     response = requests.get(
#         f"{ENV['CANDIG_URL']}/query/query", headers=headers, params=params
#     )
#     if len(response.json()["results"]) != 1:
#         print(f"\n\nExpected 1 results from the genomic query using gene name 'TPTE' but got {len(response.json()["results"])}")
#         if len(response.json()["results"]) > 0:
#             print("Got results from:")
#             for donor in response.json()["results"]:
#                 print(f"{donor["program_id"]}: {donor["submitter_donor_id"]}")
#     assert response and len(response.json()["results"]) == 1
#
#
# # Can we use a discovery query to get counts of donors we do not have access to?
# def test_query_discovery():
#     token = get_token(username=ENV['CANDIG_SITE_ADMIN_USER'],
#                       password=ENV['CANDIG_SITE_ADMIN_PASSWORD'])
#     headers = {
#         "Authorization": f"Bearer {token}",
#     }
#
#     omop_response = requests.get(
#         f"{ENV['CANDIG_URL']}/candig-api/v1/datasets", headers=headers
#     ).json()
#     query_response = requests.get(
#         f"{ENV['CANDIG_URL']}/candig-api/v1/datasets/statistics", headers=headers).json()
#     # Ensure that each category in metadata corresponds to something in the site
#     for category in query_response["site"]["required_but_missing"]:
#         for field in query_response["site"]["required_but_missing"][category]:
#             for total_type in query_response["site"]["required_but_missing"][category][field]:
#                 total = query_response["site"]["required_but_missing"][category][field][total_type]
#                 if type(total) == str:
#                     # Can't perform this check on censored data
#                     continue
#                 for program in omop_response["items"]:
#                     if category in program["metadata"]['required_but_missing'] and field in program["metadata"]['required_but_missing'][category]:
#                         if type(program["metadata"]['required_but_missing'][category][field][total_type]) == int:
#                             total -= program["metadata"]['required_but_missing'][category][field][total_type]
#                 if total != 0:
#                     print(f"{category}/{field}/{total_type} totals don't line up")
#                     assert False
#
#     # Ensure that every category & field in Katsu exists in the response
#     for program in omop_response["items"]:
#         for category in program["metadata"]["required_but_missing"]:
#             assert category in query_response["site"]["required_but_missing"]
#             for field in program["metadata"]["required_but_missing"][category]:
#                 assert field in query_response["site"]["required_but_missing"][category]
#
#
# # Can we check how many donors have genomics data?
# def test_query_completeness():
#     token = get_token(username=ENV['CANDIG_SITE_ADMIN_USER'],
#                       password=ENV['CANDIG_SITE_ADMIN_PASSWORD'])
#     headers = {
#         "Authorization": f"Bearer {token}",
#     }
#     query_response = requests.get(
#         f"{ENV['CANDIG_ENV']['QUERY_INTERNAL_URL']}/genomic_completeness", headers=headers).json()
#     pprint.pprint(query_response)
#     # Verify that the synthetic data shows up
#     assert f"{ENV['CANDIG_ENV']['CANDIG_SITE_LOCATION']}-SYNTH_01" in query_response
#     assert query_response[f"{ENV['CANDIG_ENV']['CANDIG_SITE_LOCATION']}-SYNTH_01"]["genomes"] == 6
#     assert f"{ENV['CANDIG_ENV']['CANDIG_SITE_LOCATION']}-SYNTH_02" in query_response
#     assert query_response[f"{ENV['CANDIG_ENV']['CANDIG_SITE_LOCATION']}-SYNTH_02"]["genomes"] == 5
#
#
def test_clean_up(datasets):
    for dataset in datasets:
        clean_up_dataset(dataset)

    clean_up_user(ENV['CANDIG_NOT_ADMIN_USER'])
    clean_up_user(ENV['CANDIG_NOT_ADMIN2_USER'])

    site_admin_token = get_site_admin_token()
    headers = {
        "Authorization": f"Bearer {site_admin_token}",
        "Content-Type": "application/json; charset=utf-8",
    }
    delete_response = requests.delete(
        f"{ENV['CANDIG_URL']}/candig-api/v1/authz/user/pending",
        headers=headers
    )
    # clean up test_htsget
    # old_val = os.environ.get("TESTENV_URL")
    # os.environ["TESTENV_URL"] = f"{ENV['CANDIG_ENV']['HTSGET_PUBLIC_URL']}"
    # pytest.main(["-x", "lib/htsget/htsget_app/tests/test_htsget_server.py", "-k", "test_remove_objects"])
    # if old_val is not None:
    #     os.environ["TESTENV_URL"] = old_val

