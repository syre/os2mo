#
# Copyright (c) 2017, Magenta ApS
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

import json
from . import util
from mora import lora
from tests.util import jsonfile_to_dict


class TestCreateOrgUnit(util.LoRATestCase):
    maxDiff = None

    # TODO: mock time

    def test_should_create_org_unit_with_virkning_to_infinity(self):
        self.load_sample_structures()

        root = '2874e1dc-85e6-4269-823a-e1125484dfd3'
        org = '456362c4-0ee4-4e5e-a72c-751239745e62'

        payload = {
            "user-key": "NULL",
            "name": "NyEnhed",
            "valid-from": "01-01-2010",
            "org": org,
            "parent": root,
            "type": {
                "name": "Afdeling",
                "userKey": "Afdeling",
                "uuid": "32547559-cfc1-4d97-94c6-70b192eff825"
            },
            "locations": [
                {
                    "name": "lnavn",
                    "primaer": True,
                    "location": {
                        "UUID_EnhedsAdresse":
                            "98001816-a7cc-4115-a9e6-2c5c06c79e5d",
                        "postdistrikt": "Risskov",
                        "postnr": "8240",
                        "vejnavn": "Pilevej 2, 8240 Risskov"
                    },
                    "contact-channels": [
                        {
                            "contact-info": "12345678",
                            "visibility": {
                                "name": "N/A",
                                "user-key": "N/A",
                                "uuid": "00000000-0000-0000-0000-000000000000"
                            },
                            "type": {
                                "name": "Phone Number",
                                "prefix": "urn:magenta.dk:telefon:",
                                "uuid": "b7ccfb21-f623-4e8f-80ce-89731f726224"
                            }
                        }
                    ]
                }
            ]
        }
        r = self.client.post('/o/' + org + '/org-unit',
                             data=json.dumps(payload),
                             content_type='application/json')
        self.assertEqual(201, r.status_code)

        # Get the UUID of the org unit just created
        uuid = json.loads(r.data.decode())['uuid']

        lora_response = lora.get('organisation/organisationenhed', uuid=uuid)
        lora_response.pop('fratidspunkt')

        expected_response = jsonfile_to_dict(
            'tests/integration_test_data/create_org_unit_infinity.json')
        expected_response.pop('fratidspunkt')

        self.assertEqual(expected_response, lora_response)
