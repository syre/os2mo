#
# Copyright (c) Magenta ApS
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

'''
Associations
------------

This section describes how to interact with employee associations.

'''

from . import handlers
from .. import common
from .. import exceptions
from .. import lora
from .. import mapping
from .. import util
from .. import validator


class AssociationRequestHandler(handlers.OrgFunkRequestHandler):
    __slots__ = ()

    role_type = 'association'
    function_key = mapping.ASSOCIATION_KEY

    def prepare_create(self, req):
        c = lora.Connector()

        org_unit = util.checked_get(req, mapping.ORG_UNIT,
                                    {}, required=True)
        org_unit_uuid = util.get_uuid(org_unit, required=True)

        employee = util.checked_get(req, mapping.PERSON, {}, required=True)
        employee_uuid = util.get_uuid(employee, required=True)

        org_unit_obj = c.organisationenhed.get(org_unit_uuid)

        if not org_unit_obj:
            exceptions.ErrorCodes.E_ORG_UNIT_NOT_FOUND(
                org_unit_uuid=org_unit_uuid,
            )

        org_uuid = org_unit_obj['relationer']['tilhoerer'][0]['uuid']
        association_type_uuid = util.get_mapping_uuid(
            req,
            mapping.ASSOCIATION_TYPE,
            required=True)

        valid_from, valid_to = util.get_validities(req)

        bvn = "{} {} {}".format(employee_uuid, org_unit_uuid,
                                mapping.ASSOCIATION_KEY)

        primary = req.get(mapping.PRIMARY)

        # Validation
        validator.is_date_range_in_org_unit_range(org_unit, valid_from,
                                                  valid_to)
        validator.is_date_range_in_employee_range(employee, valid_from,
                                                  valid_to)
        validator.does_employee_have_existing_association(employee_uuid,
                                                          org_unit_uuid,
                                                          valid_from)

        if primary:
            validator.does_employee_have_existing_primary_function(
                self.function_key, valid_from, valid_to, employee_uuid,
            )

        association = common.create_organisationsfunktion_payload(
            funktionsnavn=mapping.ASSOCIATION_KEY,
            primær=primary,
            valid_from=valid_from,
            valid_to=valid_to,
            brugervendtnoegle=bvn,
            tilknyttedebrugere=[employee_uuid],
            tilknyttedeorganisationer=[org_uuid],
            tilknyttedeenheder=[org_unit_uuid],
            funktionstype=association_type_uuid,
        )

        self.payload = association
        self.uuid = util.get_uuid(req, required=False)

    def prepare_edit(self, req: dict):
        association_uuid = req.get('uuid')
        # Get the current org-funktion which the user wants to change
        c = lora.Connector(virkningfra='-infinity', virkningtil='infinity')
        original = c.organisationfunktion.get(uuid=association_uuid)

        data = req.get('data')
        new_from, new_to = util.get_validities(data)

        validator.is_edit_from_date_before_today(new_from)

        # Get org unit uuid for validation purposes
        org_unit = mapping.ASSOCIATED_ORG_UNIT_FIELD(original)[0]

        payload = dict()
        payload['note'] = 'Rediger tilknytning'

        original_data = req.get('original')
        if original_data:
            # We are performing an update
            old_from, old_to = util.get_validities(original_data)
            payload = common.inactivate_old_interval(
                old_from, old_to, new_from, new_to, payload,
                ('tilstande', 'organisationfunktiongyldighed')
            )

        update_fields = list()

        # Always update gyldighed
        update_fields.append((
            mapping.ORG_FUNK_GYLDIGHED_FIELD,
            {'gyldighed': "Aktiv"}
        ))

        if mapping.ASSOCIATION_TYPE in data:
            update_fields.append((
                mapping.ORG_FUNK_TYPE_FIELD,
                {'uuid': data.get(mapping.ASSOCIATION_TYPE).get('uuid')},
            ))

        if mapping.ORG_UNIT in data:
            org_unit_uuid = data.get(mapping.ORG_UNIT).get('uuid')

            update_fields.append((
                mapping.ASSOCIATED_ORG_UNIT_FIELD,
                {'uuid': org_unit_uuid},
            ))
        else:
            org_unit_uuid = util.get_obj_uuid(
                original,
                mapping.ASSOCIATED_ORG_UNIT_FIELD.path,
            )

        if mapping.PERSON in data:
            employee = data.get(mapping.PERSON)
            employee_uuid = employee.get('uuid')

            update_fields.append((mapping.USER_FIELD, {'uuid': employee_uuid}))
        else:
            employee = util.get_obj_value(
                original, mapping.USER_FIELD.path)[-1]
            employee_uuid = util.get_uuid(employee)

        try:
            exts = mapping.ORG_FUNK_UDVIDELSER_FIELD(original)[-1].copy()
        except (TypeError, LookupError):
            exts = {}

        if mapping.PRIMARY in data:
            primary = util.checked_get(data, mapping.PRIMARY, False)

            update_fields.append((
                mapping.ORG_FUNK_UDVIDELSER_FIELD,
                {
                    **exts,
                    'primær': primary,
                },
            ))
        else:
            primary = exts.get('primær')

        payload = common.update_payload(new_from, new_to, update_fields,
                                        original,
                                        payload)

        bounds_fields = list(
            mapping.ASSOCIATION_FIELDS.difference(
                {x[0] for x in update_fields}))
        payload = common.ensure_bounds(new_from, new_to, bounds_fields,
                                       original, payload)

        # Validation
        validator.is_date_range_in_org_unit_range(org_unit, new_from,
                                                  new_to)
        validator.is_date_range_in_employee_range(employee, new_from,
                                                  new_to)
        validator.does_employee_have_existing_association(employee_uuid,
                                                          org_unit_uuid,
                                                          new_from,
                                                          association_uuid)

        if primary:
            validator.does_employee_have_existing_primary_function(
                self.function_key, new_from, new_to, employee_uuid,
            )

        self.payload = payload
        self.uuid = association_uuid
