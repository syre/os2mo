#
# Copyright (c) 2017-2018, Magenta ApS
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


'''
Employees
---------

This section describes how to interact with employees.

'''

import copy
import functools
from typing import Callable, List, Tuple

import flask

from mora.service.association import create_association
from mora.service.common import (FieldTuple, FieldTypes, set_object_value,
                                 get_obj_value)
from mora.service.engagement import (terminate_engagement, create_engagement,
                                     edit_engagement)
from . import common
from .. import util
from ..converters import reading, writing

blueprint = flask.Blueprint('employee', __name__, static_url_path='',
                            url_prefix='/service')


@blueprint.route('/o/<uuid:orgid>/e/')
@util.restrictargs('at', 'start', 'limit', 'query')
def list_employees(orgid):
    '''Query employees in an organisation.

    .. :quickref: Employee; List & search

    :param uuid orgid: UUID of the organisation to search.

    :queryparam date at: Current time in ISO-8601 format.
    :queryparam int start: Index of first unit for paging.
    :queryparam int limit: Maximum items
    :queryparam string query: Filter by employees matching this string.
        Please note that this only applies to attributes of the user, not the
        relations or engagements they have.

    :<jsonarr string name: Human-readable name.
    :<jsonarr string uuid: Machine-friendly UUID.

    :status 200: Always.

    **Example Response**:

    .. sourcecode:: json

      [
        {
          "name": "Hans Bruger",
          "uuid": "9917e91c-e3ee-41bf-9a60-b024c23b5fe3"
        },
        {
          "name": "Joe User",
          "uuid": "cd2dcfad-6d34-4553-9fee-a7023139a9e8"
        }
      ]

    '''

    # TODO: share code with list_orgunits?

    c = common.get_connector()

    args = flask.request.args

    kwargs = dict(
        limit=int(args.get('limit', 0)) or 20,
        start=int(args.get('start', 0)) or 0,
        tilhoerer=str(orgid),

        # this makes the search go slow :(
        gyldighed='Aktiv',
    )

    if 'query' in args:
        kwargs.update(vilkaarligattr='%{}%'.format(args['query']))

    return flask.jsonify([
        {
            'name': bruger['attributter']['brugeregenskaber'][0]['brugernavn'],
            'uuid': brugerid,
        }
        for brugerid, bruger in c.bruger.get_all(**kwargs)
    ])


@blueprint.route('/e/<uuid:id>/')
@util.restrictargs('at')
def get_employee(id, raw=False):
    '''Retrieve an employee.

    .. :quickref: Employee; Get

    :queryparam date at: Current time in ISO-8601 format.

    :<json string name: Human-readable name.
    :<json string uuid: Machine-friendly UUID.
    :<json string cpr_no: CPR number of for the corresponding person.

    :status 200: Whenever the user ID is valid and corresponds to an
        existing user.
    :status 404: Otherwise.

    **Example Response**:

    .. sourcecode:: json

      {
        "cpr_no": "1011101010",
        "name": "Hans Bruger",
        "uuid": "9917e91c-e3ee-41bf-9a60-b024c23b5fe3"
      }

    '''
    c = common.get_connector()

    user = c.bruger.get(id)

    r = {
        'uuid': id,

        'name':
            user['attributter']
            ['brugeregenskaber'][0]
            ['brugernavn'],

        'cpr_no':
            user['relationer']
            ['tilknyttedepersoner'][0]
            ['urn'].rsplit(':', 1)[-1],
    }

    if raw:
        return r
    else:
        return flask.jsonify(r)


@blueprint.route('/e/<uuid:employee_uuid>/create', methods=['POST'])
def create_employee(employee_uuid):
    """Creates new mapping relations

    .. :quickref: Employee; Create

    :statuscode 200: Creation succeeded.

    :param employee_uuid: The UUID of the mapping.

    **Example Request**:

    Request payload contains a list of creation objects, each differentiated
    by the attribute 'type'. Each of these object types are detailed below:

    **Engagement**:

    :<jsonarr string type: **"engagement"**
    :<jsonarr string org_unit_uuid: The UUID of the associated org unit
    :<jsonarr string org_uuid: The UUID of the associated organisation
    :<jsonarr string job_title_uuid: The UUID of the job title of the engagment
    :<jsonarr string engagement_type_uuid: The UUID of the engagement type
    :<jsonarr string valid_from: The date from which the role should be valid,
        in ISO 8601.
    :<jsonarr string valid_to: The date which the role should be valid to,
        in ISO 8601.

    .. sourcecode:: json

      [
        {
          "type": "engagement",
          "org_unit": {
            "uuid": "a30f5f68-9c0d-44e9-afc9-04e58f52dfec"
          },
          "org": {
            "uuid": "f494ad89-039d-478e-91f2-a63566554bd6"
          },
          "job_title": {
            "uuid": "3ef81e52-0deb-487d-9d0e-a69bbe0277d8"
          },
          "engagement_type": {
            "uuid": "62ec821f-4179-4758-bfdf-134529d186e9"
          },
          "valid_from": "2016-01-01T00:00:00+00:00",
          "valid_to": "2018-01-01T00:00:00+00:00"
        }
      ]

    **Association**:

    :<jsonarr string type: **"association"**
    :<jsonarr string org_unit_uuid: The UUID of the associated org unit
    :<jsonarr string org_uuid: The UUID of the associated organisation
    :<jsonarr string job_title_uuid: The UUID of the job title of the
        association
    :<jsonarr string association_type_uuid: The UUID of the association type
    :<jsonarr string valid_from: The date from which the role should be valid,
        in ISO 8601.
    :<jsonarr string valid_to: The date which the role should be valid to,
        in ISO 8601.

    .. sourcecode:: json

      [
        {
          "type": "association",
          "org_unit": {
            "uuid": "a30f5f68-9c0d-44e9-afc9-04e58f52dfec"
          },
          "org": {
            "uuid": "f494ad89-039d-478e-91f2-a63566554bd6"
          },
          "job_title": {
            "uuid": "3ef81e52-0deb-487d-9d0e-a69bbe0277d8"
          },
          "engagement_type": {
            "uuid": "62ec821f-4179-4758-bfdf-134529d186e9"
          },
          "valid_from": "2016-01-01T00:00:00+00:00",
          "valid_to": "2018-01-01T00:00:00+00:00"
        }
      ]

    **IT**:

    **Leader**:

    **Role**:

    """

    handlers = {
        'engagement': create_engagement,
        'association': create_association,
        # 'it': create_it,
        # 'role': create_role,
        'contact': writing.create_contact,
        # 'leader': create_leader,
        # 'absence': create_absence,
    }

    reqs = flask.request.get_json()
    for req in reqs:
        role_type = req.get('type')
        handler = handlers.get(role_type)

        # TODO: Find a better way to handle this, probably
        if not req.get('valid_to'):
            req['valid_to'] = 'infinity'

        if not handler:
            return flask.jsonify('Unknown role type'), 400

        # TODO: Find a better way to handle this...
        if not req.get('valid_to'):
            req['valid_to'] = 'infinity'

        handler(str(employee_uuid), req)

    # TODO:
    return flask.jsonify(employee_uuid), 200


@blueprint.route('/e/<uuid:employee_uuid>/edit', methods=['POST'])
def edit_employee(employee_uuid):
    """Edits an mapping

    .. :quickref: Employee; Edit mapping

    :statuscode 200: The edit succeeded.

    **Example Request**:

    Request payload contains a list of edit objects, each differentiated
    by the attribute 'type'. Each of these object types are detailed below:

    **Engagement**:

    :param employee_uuid: The UUID of the mapping to be moved.

    :<json string type: **"engagement"**
    :<json string uuid: The UUID of the engagement,
    :<json object overwrite: An **optional** object containing the original
        state of the engagement to be overwritten. If supplied, the change
        will modify the existing registration on the engagement object.
        Detailed below. Note, this object is only optional for *engagement*.
    :<json object data: An object containing the changes to be made to the
        engagement. Detailed below.

    The **overwrite** and **data** objects follow the same structure.
    Every field in **overwrite** is required, whereas **data** only needs
    to contain the fields that need to change along with the validity dates.

    :<jsonarr string valid_from: The from date, in ISO 8601.
    :<jsonarr string valid_to: The to date, in ISO 8601.
    :<jsonarr string org_unit_uuid: The UUID of the associated org unit
    :<jsonarr string job_title_uuid: The UUID of the job title of the
        engagement
    :<jsonarr string engagement_type_uuid: The UUID of the engagement type

    .. sourcecode:: json

      [
        {
          "type": "engagement",
          "uuid": "de9e7513-1934-481f-b8c8-45336387e9cb",
          "overwrite": {
            "valid_from": "2016-01-01T00:00:00+00:00",
            "valid_to": "2018-01-01T00:00:00+00:00",
            "job_title": {
              "uuid": "5b56432c-f289-4d81-a328-b878ea0a4e1b"
            },
            "engagement_type": {
              "uuid": "743a6448-2b0b-48cf-8a2e-bf938a6181ee"
            },
            "org_unit": {
              "uuid": "04f73c63-1e01-4529-af2b-dee36f7c83cb"
            }
          },
          "data": {
            "valid_from": "2016-01-01T00:00:00+00:00",
            "valid_to": "2019-01-01T00:00:00+00:00",
            "job_title": {
              "uuid": "5b56432c-f289-4d81-a328-b878ea0a4e1b"
            }
          }
        }
      ]

    **Association**:

    :param employee_uuid: The UUID of the mapping to be moved.

    :<json string type: **"association"**
    :<json string uuid: The UUID of the association,
    :<json object overwrite: An object containing the original state
        of the association to be overwritten. If supplied, the change will
        modify the existing registration on the engagement object.
        Detailed below.
    :<json object data: An object containing the changes to be made to the
        engagement. Detailed below.

    The **overwrite** and **data** objects follow the same structure.
    Every field in **overwrite** is required, whereas **data** only needs
    to contain the fields that need to change along with the validity dates.

    :<jsonarr string valid_from: The from date, in ISO 8601.
    :<jsonarr string valid_to: The to date, in ISO 8601.
    :<jsonarr string org_unit_uuid: The UUID of the associated org unit
    :<jsonarr string job_title_uuid: The UUID of the job title of the
        engagement
    :<jsonarr string association_type_uuid: The UUID of the association type

    .. sourcecode:: json

      [
        {
          "type": "association",
          "uuid": "de9e7513-1934-481f-b8c8-45336387e9cb",
          "overwrite": {
            "valid_from": "2016-01-01T00:00:00+00:00",
            "valid_to": "2018-01-01T00:00:00+00:00",
            "job_title": {
              "uuid": "5b56432c-f289-4d81-a328-b878ea0a4e1b"
            },
            "association_type": {
              "uuid": "743a6448-2b0b-48cf-8a2e-bf938a6181ee"
            },
            "org_unit": {
              "uuid": "04f73c63-1e01-4529-af2b-dee36f7c83cb"
            }
          },
          "data": {
            "valid_from": "2016-01-01T00:00:00+00:00",
            "valid_to": "2019-01-01T00:00:00+00:00",
            "job_title": {
              "uuid": "5b56432c-f289-4d81-a328-b878ea0a4e1b"
            }
          }
        }
      ]
    """

    handlers = {
        'engagement': edit_engagement
        # 'association': edit_association,
        # 'it': edit_it,
        # 'contact': edit_contact,
        # 'leader': edit_leader,
    }

    reqs = flask.request.get_json()

    for req in reqs:
        role_type = req.get('type')
        handler = handlers.get(role_type)

        # TODO: Find a better way to handle this, probably
        if not req.get('data').get('valid_to'):
            req['data']['valid_to'] = 'infinity'

        if not handler:
            return flask.jsonify('Unknown role type'), 400

        handler(str(employee_uuid), req)

    # TODO: Figure out the response
    return flask.jsonify(employee_uuid), 200


@blueprint.route('/e/<uuid:employee_uuid>/terminate', methods=['POST'])
def terminate_employee(employee_uuid):
    """Terminates an mapping and all of his roles from a specified date.

    .. :quickref: Employee; Terminate

    :statuscode 200: The termination succeeded.

    :param employee_uuid: The UUID of the mapping to be terminated.

    :<json string valid_from: The date on which the termination should happen,
                              in ISO 8601.

    **Example Request**:

    .. sourcecode:: json

      {
        "valid_from": "2016-01-01T00:00:00+00:00"
      }
    """
    date = flask.request.get_json().get('valid_from')

    engagements = reading.get_engagements(userid=employee_uuid,
                                          effective_date=date)
    for engagement in engagements:
        engagement_uuid = engagement.get('uuid')
        terminate_engagement(engagement_uuid, date)

    # TODO: Terminate Tilknytning
    # TODO: Terminate IT
    # TODO: Terminate Kontakt
    # TODO: Terminate Rolle
    # TODO: Terminate Leder
    # TODO: Terminate Orlov

    # TODO:
    return flask.jsonify(employee_uuid), 200
