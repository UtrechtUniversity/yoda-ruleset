# coding=utf-8
"""Meta form API feature tests."""

__copyright__ = 'Copyright (c) 2020-2022, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

from pytest_bdd import (
    given,
    parsers,
    scenarios,
    then,
)

from conftest import api_request

scenarios('../../features/api/api_meta_form.feature')

LONG_METADATA = {
    "links": [
        {
            "rel": "describedby",
            "href": "https://yoda.uu.nl/schemas/default-0/metadata.json"
        }
    ],
    "Discipline": [
        "Natural Sciences - Computer and information sciences (1.2)"
    ],
    "Language": "en - English",
    "Collected": {
        "Start_Date": "2021-07-01",
        "End_Date": "2021-07-12"
    },
    "Covered_Geolocation_Place": [
        "Heidelberglaan 8, 3584 CS, Utrecht, Netherlands"
    ],
    "Covered_Period": {
        "Start_Date": "2021-07-02",
        "End_Date": "2021-07-11"
    },
    "Tag": [
        "Tag_youre_it",
        "No_tag_backs"
    ],
    "Related_Datapackage": [
        {
            "Persistent_Identifier": {
                "Identifier_Scheme": "ARK",
                "Identifier": "Some_id1234"
            },
            "Relation_Type": "IsNewVersionOf: Current datapackage is new version of",
            "Title": "Some data package"
        }
    ],
    "Retention_Period": 10,
    "Funding_Reference": [
        {
            "Funder_Name": "Big organisation with money",
            "Award_Number": "Super award #42"
        }
    ],
    "Creator": [
        {
            "Name": {
                "Given_Name": "María José",
                "Family_Name": "Carreño Quiñones"
            },
            "Affiliation": [
                "Utrecht University"
            ],
            "Person_Identifier": [
                {
                    "Name_Identifier_Scheme": "ORCID",
                    "Name_Identifier": "Orchid_flower"
                }
            ],
        },
        {
            "Name": {
                "Given_Name": "Борис",
                "Family_Name": "Николаевич Ельцин"
            },
            "Affiliation": [
                "Utrecht University"
            ],
            "Person_Identifier": [
                {}
            ]
        }
    ],
    "Contributor": [
        {
            "Name": {
                "Given_Name": "Tấn Dũng",
                "Family_Name": "Nguyễn"
            },
            "Contributor_Type": "ContactPerson",
            "Person_Identifier": [
                {
                    "Name_Identifier_Scheme": "ORCID",
                    "Name_Identifier": "Orchid_2"
                }
            ],
            "Affiliation": [
                "University of Göttingen"
            ]
        },
        {
            "Name": {
                "Given_Name": "Björk",
                "Family_Name": "Guðmundsdóttir"
            },
            "Affiliation": [
                "École des Beaux-Arts"
            ]
        }
    ],
    "Data_Access_Restriction": "Restricted - available upon request",
    "Title": "Title of the data package",
    "Description": "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Nulla vulputate, nulla a sollicitudin cursus, est nisl mattis nunc, nec convallis lectus libero eget dolor. Donec id nibh diam. Maecenas sagittis lacus at laoreet sodales. Phasellus sit amet pretium lorem. Class aptent taciti sociosqu ad litora torquent per conubia nostra, per inceptos himenaeos. Pellentesque sed ante vel dolor convallis vestibulum. Donec non blandit lorem, vitae pulvinar sem. Nullam a varius arcu. Etiam et nulla ante. Cras fermentum quis mauris id elementum. Proin est ante, iaculis eget tempor ac, ultrices tincidunt arcu.\n\nMorbi non finibus turpis, et maximus nisi. Donec nisi mauris, ultrices sit amet leo ut, egestas lacinia sapien. Donec ut elit a sapien blandit pellentesque. Ut tincidunt tortor a justo vulputate maximus. Maecenas vitae ullamcorper massa, ut faucibus ipsum. Fusce vulputate, tellus et cursus pretium, dolor quam ullamcorper dui, nec sollicitudin purus quam in est. Pellentesque purus risus, tristique rutrum erat vitae, cursus suscipit ipsum. Nam vehicula congue leo, sed accumsan massa blandit commodo. Maecenas id tortor elementum, consequat nibh vel, aliquet purus. Vestibulum ante ipsum primis in faucibus orci luctus et ultrices posuere cubilia curae; Sed euismod ac velit ac facilisis. Fusce quis viverra mi. In sit amet ante et felis porta accumsan at nec turpis. Maecenas venenatis nec dui quis hendrerit.\n\nClass aptent taciti sociosqu ad litora torquent per conubia nostra, per inceptos himenaeos. Etiam ut nisi fringilla felis posuere tempor. Duis mi ligula, pellentesque et mi sed, laoreet venenatis justo. Lorem ipsum dolor sit amet, consectetur adipiscing elit. Nam in tincidunt ante. Nam ullamcorper felis eu metus fringilla, eu mollis purus faucibus. Pellentesque et pulvinar eros. In hac habitasse platea dictumst.\n\nDonec blandit, lacus et lobortis vulputate, leo purus tempus urna, vulputate porta nisi nulla eget quam. Sed vitae turpis risus. In hac habitasse platea dictumst. Pellentesque feugiat libero turpis, sed scelerisque libero rutrum in. Sed non sagittis ligula. Maecenas congue metus magna, ut sollicitudin leo mattis sed. Nunc sodales nec mi eget commodo. Praesent consectetur quis sapien ut vehicula.\n\nPhasellus vitae justo sed ipsum aliquet pretium. Nam posuere posuere ipsum eget efficitur. Morbi ultrices in est non posuere. Nulla dignissim libero sed mi tincidunt, sit amet mattis nunc iaculis. Mauris nunc erat, maximus sit amet sem vel, mattis vestibulum diam. Pellentesque libero lacus, fermentum finibus purus nec, bibendum auctor magna. Curabitur nisl purus, tristique in tempor tincidunt, molestie vitae lectus.Lorem ipsum dolor sit amet, consectetur adipis",
    "Version": "3.384",
    "Data_Classification": "Public",
    "License": "Creative Commons Attribution 4.0 International Public License",
    "Retention_Information": "Retention information: 10 years is just right",
    "Embargo_End_Date": "2021-07-22",
    "Collection_Name": "Yoda test project"
}


@given(parsers.parse("the Yoda meta form save API is queried with metadata and {collection}"), target_fixture="api_response")
def api_meta_form_save(user, collection):
    return api_request(
        user,
        "meta_form_save",
        {"coll": collection,
         "metadata": {
             "links": [{
                 "rel": "describedby",
                 "href": "https://yoda.uu.nl/schemas/default-1/metadata.json"
             }],
             "Discipline": [
                 "Natural Sciences - Computer and information sciences (1.2)"
             ],
             "Tag": [
                 "api_test"
             ],
             "Language": "en - English",
             "Retention_Period": 10,
             "Creator": [{
                 "Name": {
                     "Given_Name": "Test",
                     "Family_Name": "Test"
                 },
                 "Affiliation": ["Utrecht University"],
                 "Person_Identifier": [{}]
             }],
             "Data_Access_Restriction": "Restricted - available upon request",
             "Title": "Test",
             "Description": "Test",
             "Data_Type": "Dataset",
             "Data_Classification": "Public",
             "License": "Creative Commons Attribution 4.0 International Public License"
         }}
    )


@given(parsers.parse("the Yoda meta form save API is queried with long metadata and {collection}"), target_fixture="api_response")
def api_meta_form_save_long(user, collection):
    return api_request(
        user,
        "meta_form_save",
        {"coll": collection, "metadata": LONG_METADATA}

    )


@given(parsers.parse("the Yoda meta form load API is queried with {collection}"), target_fixture="api_response")
def api_meta_form_load(user, collection):
    return api_request(
        user,
        "meta_form_load",
        {"coll": collection}
    )


@given(parsers.parse("data package exists in {vault}"), target_fixture="data_package")
def api_vault_data_package(user, vault):
    http_status, body = api_request(
        user,
        "browse_collections",
        {"coll": vault, "sort_order": "desc"}
    )

    assert http_status == 200
    assert len(body["data"]["items"]) > 0

    return body["data"]["items"][0]["name"]


@then(parsers.parse("file {file} exists in {collection}"))
def file_exists(user, file, collection):
    http_status, body = api_request(
        user,
        "browse_folder",
        {"coll": collection}
    )

    assert http_status == 200

    # Check if folder is in browse results of collection.
    found = False
    for item in body['data']['items']:
        if item["name"] == file:
            found = True

    assert found


@then(parsers.parse("metadata is returned for {collection}"))
def metadata_returned(api_response, collection):
    http_status, body = api_response

    assert http_status == 200
