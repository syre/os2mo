#
# Copyright (c) 2017, Magenta ApS
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

import os

import flask

from . import lora
from . import util
from . import validator
from .converters import addr
from .converters import reading
from .converters import writing

basedir = os.path.dirname(__file__)
staticdir = os.path.join(basedir, 'static')

blueprint = app = flask.Blueprint('api', __name__, static_url_path='')


@app.route('/o/')
def list_organisations():
    return flask.jsonify(reading.list_organisations())


#
# EMPLOYEES
#

@app.route('/e/')
@util.restrictargs('limit', 'query', 'start')
def list_employees():
    limit = int(flask.request.args.get('limit', 100))
    start = int(flask.request.args.get('start', 0))
    query = flask.request.args.get('query')

    if query:
        search = {
            'vilkaarligattr': '%{}%'.format(query),
        }
    else:
        search = {
            'bvn': '%',
        }

    ids = reading.list_employees(
        limit=limit,
        start=start,
        **search,
    )

    return flask.jsonify(
        reading.get_employees(
            ids,
        )
    )


@app.route('/e/<int(fixed_digits=10):cpr_number>/')
@util.restrictargs()
def get_employee_by_cpr(cpr_number):
    ids = reading.list_employees(
        tilknyttedepersoner='urn:dk:cpr:person:{:010d}'.format(cpr_number),
    )

    if not ids:
        return flask.jsonify({
            'message': 'no such user',
        }), 404
    elif len(ids) > 1:
        return flask.jsonify({
            'message': 'multiple users found',
        }), 404

    return flask.jsonify(reading.get_employees(ids)[0])


@app.route('/e/<uuid:id>/')
@util.restrictargs()
def get_employee(id):
    return flask.jsonify(reading.get_employees([id])[0])


# --- Writing to LoRa --- #
@app.route('/e/<uuid:employee_uuid>/actions/move', methods=['POST'])
def move_employee(employee_uuid):
    org_unit_uuid = flask.request.args.get('org-unit')
    date = flask.request.args.get('date')

    req = flask.request.get_json()

    present_engagements = req.get('presentEngagementIds')
    future_engagements = req.get('futureEngagementIds')
    # TODO: Handle tilknytning

    c = lora.Connector(effective_date=date)
    for engagement in present_engagements:
        engagement_uuid = engagement.get('uuid')

        # Fetch current orgfunk
        orgfunk = c.organisationfunktion.get(engagement_uuid)

        # Fetch current engagement start and end
        virkning = get_orgfunk_virkning(orgfunk)
        startdate = virkning.get('from')
        enddate = virkning.get('to')

        # Inactivate the current orgfunk at the move date
        inactivate_payload = writing.inactivate_org_funktion(startdate,
                                                             date)
        c.organisationfunktion.update(inactivate_payload, engagement_uuid)

        # Create new orgfunk active from the move date, with new org unit
        new_orgfunk_payload = writing.move_org_funktion(orgfunk, org_unit_uuid,
                                                        date, enddate)
        c.organisationfunktion.create(new_orgfunk_payload)

    c = lora.Connector(effective_date=date, validity='future')
    for engagement in future_engagements:
        engagement_uuid = engagement.get('uuid')

        orgfunk = c.organisationfunktion.get(engagement_uuid)

        virkning = get_orgfunk_virkning(orgfunk)
        startdate = virkning.get('from')
        enddate = virkning.get('to')

        if engagement.get('overwrite') == 1:
            # Inactivate original orgfunk
            inactivate_payload = writing.fully_inactivate_org_funktion(
                startdate, enddate)
            c.organisationfunktion.update(inactivate_payload, engagement_uuid)
            # Create new orgfunk with new enhed from move date
            new_orgfunk_payload = writing.move_org_funktion(orgfunk,
                                                            org_unit_uuid,
                                                            date, enddate)
            c.organisationfunktion.create(new_orgfunk_payload)
        elif engagement.get('overwrite') == 0:
            # Create new orgfunk active from the move date, to the start of
            # the original orgfunk
            new_orgfunk_payload = writing.move_org_funktion(orgfunk,
                                                            org_unit_uuid,
                                                            date, startdate)
            c.organisationfunktion.create(new_orgfunk_payload)

    return flask.jsonify([]), 200


def get_orgfunk_virkning(orgfunk):
    return [
        g['virkning'] for g in
        orgfunk['tilstande']['organisationfunktiongyldighed']
        if g['gyldighed'] == 'Aktiv'
    ][0]


@app.route('/e/<uuid:employee_uuid>/actions/terminate', methods=['POST'])
def terminate_employee(employee_uuid):
    date = flask.request.args.get('date')

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

    return flask.jsonify(employee_uuid), 200


def terminate_engagement(engagement_uuid, enddate):
    c = lora.Connector(effective_date=enddate)

    orgfunk = c.organisationfunktion.get(engagement_uuid)

    # Create inactivation object
    virkning = get_orgfunk_virkning(orgfunk)
    startdate = virkning.get('from')

    payload = writing.inactivate_org_funktion(startdate, enddate)
    c.organisationfunktion.update(payload, engagement_uuid)


@app.route('/mo/e/<uuid:brugerid>/actions/role', methods=['POST'])
def create_employee_role(brugerid):
    """
    Catch-all function for creating Employees roles

    :param brugerid:  BrugerID from MO. Not used.
    :return:
    """
    reqs = flask.request.get_json()

    for req in reqs:
        c = lora.Connector()
        role_type = req.get('role-type')

        handlers = {
            'engagement': create_engagement,
            # 'association': create_association,
            # 'it': create_it,
            # 'contact': create_contact,
            # 'leader': create_leader,
        }

        handler = handlers.get(role_type)

        if not handler:
            return flask.jsonify(
                {'message': 'unsupported role type {}'.format(role_type)}), 400

        handler(req, c)

    return flask.jsonify('Success'), 200


def create_engagement(req, c):
    # TODO: Validation
    engagement = writing.create_org_funktion(req)
    c.organisationfunktion.create(engagement)


@app.route('/o/<uuid:orgid>/org-unit', methods=['POST'])
def create_organisation_unit(orgid):
    """
    Create a new org unit.

    :param orgid: The UUID of the organisation (not used, but given by the
        frontend).
    :return: JSON containing the new org unit UUID and the response status
        code.
    """

    req = flask.request.get_json()
    if not validator.is_create_org_unit_request_valid(req):
        return flask.jsonify(validator.ERRORS['create_org_unit']), 400

    org_unit = writing.create_org_unit(req)
    uuid = lora.create('organisation/organisationenhed', org_unit)

    return flask.jsonify({'uuid': uuid}), 201


@app.route('/o/<uuid:orgid>/org-unit/<uuid:unitid>', methods=['DELETE'])
@util.restrictargs('endDate')
def inactivate_org_unit(orgid, unitid):
    """
    Inactivate an org unit.

    :param orgid: The UUID of the organisation (not used, but given by the
        frontend).
    :param unitid: The UUID of the org unit.
    :return: JSON containing the org unit UUID and the response status code.
    """

    enddate = flask.request.args.get('endDate')
    if not validator.is_inactivation_date_valid(str(unitid), enddate):
        return flask.jsonify(validator.ERRORS['inactivate_org_unit']), 400

    update_url = 'organisation/organisationenhed/%s' % unitid

    # Keep the calls to LoRa in app.py (makes it easier to test writing.py)
    org_unit = lora.get_org_unit(unitid)
    startdate = [
        g['virkning']['from'] for g in
        org_unit['tilstande']['organisationenhedgyldighed']
        if g['gyldighed'] == 'Aktiv'
    ]
    assert len(startdate) == 1  # We only support one active period for now
    startdate = startdate[0]

    # Delete org data for validity first - only way to do it in LoRa
    lora.update(update_url, {'tilstande': {'organisationenhedgyldighed': []}})

    # Then upload payload with actual virkninger
    payload = writing.inactivate_org_unit(startdate, enddate)
    lora.update(update_url, payload)

    return flask.jsonify({'uuid': unitid}), 200


@app.route('/o/<uuid:orgid>/org-unit/<uuid:unitid>/actions/move',
           methods=['POST'])
@util.restrictargs()
def move_org_unit(orgid, unitid):
    """
    Move an org unit.

    :param orgid: The UUID of the organisation (not used, but given by the
        frontend).
    :param unitid: The UUID of the org unit.
    :return: JSON containing the org unit UUID and the response status code.
    """

    # TODO: refactor common behavior from this route and the one below

    req = flask.request.get_json()
    if not validator.is_candidate_parent_valid(str(unitid), req):
        return flask.jsonify(validator.ERRORS['rename_org_unit']), 400

    payload = writing.move_org_unit(req)
    lora.update('organisation/organisationenhed/%s' % unitid, payload)

    return flask.jsonify({'uuid': unitid}), 200


@app.route('/o/<uuid:orgid>/org-unit/<uuid:unitid>', methods=['POST'])
@util.restrictargs('rename')
def rename_or_retype_org_unit(orgid, unitid):
    """
    Change the name or the type of an org unit.

    :param orgid: The UUID of the organisation.
    :param unitid: The UUID of the org unit.
    :return: JSON containing the org unit UUID and the response status code.
    """

    rename = flask.request.args.get('rename', None)

    req = flask.request.get_json()

    if rename:
        # Renaming an org unit
        payload = writing.rename_org_unit(req)
    else:
        # Changing the org units enhedstype
        assert req['type']
        payload = writing.retype_org_unit(req)

    lora.update('organisation/organisationenhed/%s' % unitid, payload)

    return flask.jsonify({'uuid': unitid}), 200


@app.route(
    '/o/<uuid:orgid>/org-unit/<uuid:unitid>/role-types/location',
    methods=['POST'],
)
@app.route(
    '/o/<uuid:orgid>/org-unit/<uuid:unitid>/role-types/location/<uuid:locid>',
    methods=['POST'],
)
def update_organisation_unit_location(orgid, unitid, locid=None):
    """
    Add a location or contact channel or update existing ones.

    :param orgid: The UUID of the organisation.
    :param unitid: The UUID of the org unit.
    :param locid: The UUID of the location (i.e. the address UUID).
    :return: JSON containing the org unit UUID and the response status code.
    """

    req = flask.request.get_json()
    if not validator.is_location_update_valid(req):
        return flask.jsonify(validator.ERRORS['update_existing_location']), 400

    kwargs = writing.create_update_kwargs(req)
    payload = writing.update_org_unit_addresses(
        unitid, **kwargs)

    if payload['relationer']['adresser']:
        lora.update('organisation/organisationenhed/%s' % unitid, payload)

    return flask.jsonify({'uuid': unitid}), 200


@app.route('/o/<uuid:orgid>/full-hierarchy')
@util.restrictargs('treeType', 'orgUnitId', 'query',
                   'effective-date', 't')
def full_hierarchy(orgid):
    args = flask.request.args

    params = dict(
        effective_date=args.get('effective-date', None),
        include_children=True,
    )

    if args.get('query'):
        # TODO: the query argument does sub-tree searching -- given
        # that LoRA has no notion of the organisation tree, we'd have
        # to emulate it
        raise ValueError('sub-tree searching is unsupported!')

    if args.get('treeType', None) == 'specific':
        r = reading.full_hierarchy(str(orgid), args['orgUnitId'], **params)

        if r:
            return flask.jsonify(
                r['children'],
            )
        else:
            return '', 404

    else:
        r = reading.full_hierarchies(str(orgid), str(orgid), **params)

        if r:
            c = lora.Connector(effective_date=args.get('effective-date', None))

            return flask.jsonify(reading.wrap_in_org(c, str(orgid), r[0]))
        else:
            return '', 404


@app.route('/o/<uuid:orgid>/org-unit/')
@app.route('/o/<uuid:orgid>/org-unit/<uuid:unitid>/')
@util.restrictargs('query', 'validity', 'effective-date', 'limit', 'start',
                   't')
def get_orgunit(orgid, unitid=None):
    # TODO: we are not actually using the 't' parameter - we should
    # probably remove this from the frontend calls later on...

    query = flask.request.args.get('query')

    if bool(unitid) is bool(query) is True:
        raise ValueError('unitid and query cannot both be set!')

    unitids = reading.list_orgunits(
        unitid or query,
        tilhoerer=str(orgid),
        effective_date=flask.request.args.get('effective-date', None),
    )

    r = reading.get_orgunits(
        str(orgid), unitids,
        validity=flask.request.args.get('validity', None),
    )

    return flask.jsonify(r) if r else ('', 404)


@app.route('/o/<uuid:orgid>/org-unit/<uuid:unitid>/history/')
@util.restrictargs('t')
def get_orgunit_history(orgid, unitid):
    # TODO: we are not actually using the 't' parameter - we should
    # probably remove this from the frontend calls later on...

    r = reading.unit_history(str(orgid), str(unitid))

    return flask.jsonify(list(r)) if r else ('', 404)


ROLE_TYPES = {
    'engagement': reading.get_engagements,
    'contact-channel': reading.get_contact_channels,
    'location': reading.get_locations,
}
ROLE_TYPE_SUFFIX = '<any({}):role>/'.format(','.join(map(repr, ROLE_TYPES)))


@app.route('/e/<uuid:userid>/role-types/' + ROLE_TYPE_SUFFIX)
@app.route('/o/<uuid:orgid>/org-unit/<uuid:unitid>/role-types/' +
           ROLE_TYPE_SUFFIX)
@util.restrictargs('effective-date', 'validity', 't')
def get_role(role, **kwargs):
    validity = flask.request.args.get('validity')
    effective_date = flask.request.args.get('effective-date')

    r = ROLE_TYPES[role](validity=validity,
                         effective_date=effective_date,
                         **kwargs)

    if r:
        return flask.jsonify(r)
    else:
        return '', 404


#
# Classification stuff - should be moved to own file
#

# This one is used when creating new "Enheder"
@app.route('/org-unit/type')
@util.restrictargs()
def list_classes():
    # TODO: require an organisation parameter

    return flask.jsonify(reading.get_classes("Enhedstype"))


@app.route(
    '/role-types/engagement/facets/<any("type", "job-title"):facet>/classes/',
)
@util.restrictargs()
def get_engagement_classes(facet):
    # TODO: require a unit or organisation parameter?

    return flask.jsonify(reading.get_classes({
        "type": "Funktionstype",
        "job-title": "Stillingsbetegnelse",
    }[facet]))

    return flask.jsonify(reading.get_contact_types())


@app.route('/addressws/geographical-location')
@util.restrictargs('local', required=['vejnavn'])
def get_geographical_addresses():
    return flask.jsonify(
        addr.autocomplete_address(flask.request.args['vejnavn'],
                                  flask.request.args.get('local')),
    )


@util.restrictargs()
@app.route('/role-types/contact/facets/properties/classes/')
def get_contact_facet_properties_classes():
    return flask.jsonify(reading.get_contact_properties())


@util.restrictargs(required=['facetKey'])
@app.route('/role-types/contact/facets/type/classes/')
def get_contact_facet_types_classes():
    key = flask.request.args['facetKey']
    assert key == 'Contact_channel_location', 'unknown key: ' + key

    return flask.jsonify(reading.get_contact_types())
