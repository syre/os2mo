# SPDX-FileCopyrightText: 2019-2020 Magenta ApS
# SPDX-License-Identifier: MPL-2.0

import abc

from mora import lora
from mora.service import facet
from ... import exceptions
from ... import mapping
from ... import util

ADDRESS_HANDLERS = {}


class _AddressHandlerMeta(abc.ABCMeta):
    """Metaclass for automatically registering handlers."""

    @staticmethod
    def __new__(mcls, name, bases, namespace):
        cls = super().__new__(mcls, name, bases, namespace)

        cls._register()

        return cls


class AddressHandler(metaclass=_AddressHandlerMeta):
    scope = None
    prefix = None
    _value = None

    @classmethod
    def _register(cls):
        ADDRESS_HANDLERS[cls.scope] = cls

    def __init__(self, value, visibility):
        self.visibility = visibility
        self._value = value

    @classmethod
    def from_effect(cls, effect):
        """Initialize handler from LoRa object"""
        # Cut off the prefix
        urn = mapping.SINGLE_ADDRESS_FIELD(effect)[0].get('urn')
        value = urn[len(cls.prefix):]

        visibility_field = mapping.VISIBILITY_FIELD(effect)
        visibility = visibility_field[0]['uuid'] if visibility_field else None

        return cls(value, visibility)

    @classmethod
    def from_request(cls, request):
        """Initialize handler from MO object"""
        value = util.checked_get(request, mapping.VALUE, "", required=True)
        cls.validate_value(value)

        visibility = util.get_mapping_uuid(
            request, mapping.VISIBILITY, required=False)

        return cls(value, visibility)

    @staticmethod
    @abc.abstractmethod
    def validate_value(value):
        """Validate that the address value is correctly formed"""
        pass

    @property
    def urn(self):
        """The value plus URN prefix"""
        return self.prefix + self._value

    @property
    def value(self):
        """The editable value"""
        return self._value

    @property
    def name(self):
        """The pretty human-readable value"""
        return self._value

    @property
    def href(self):
        """A hyperlink based on the value, if any"""
        return None

    def get_lora_properties(self):
        """
        Get a LoRa object fragment for the properties.

        The properties are used to further describe the individual
        address subtypes. E.g. visibility.

        Example::

          [{
            'objekttype': 'synlighed',
            'uuid': 'd99b500c-34b4-4771-9381-5c989eede969'
          }]
        """
        properties = []
        if self.visibility:
            properties.append(
                {
                    'objekttype': 'synlighed',
                    'uuid': self.visibility
                }
            )
        return properties

    def get_lora_address(self):
        """
        Get a LoRa object fragment for the address

        Example::

          {
            'objekttype': 'PHONE',
            'urn': 'urn:magenta.dk:telefon:+4512345678'
          }
        """
        return {
            'objekttype': self.scope,
            'urn': self.urn,
        }

    def _get_mo_properties(self):
        """
        Get a MO object fragment for the properties.

        The properties are used to further describe the individual
        address subtypes. E.g. visibility.

        Example::

          {
            'visibility': {
                'uuid': visibility
            }
          }
        """
        properties = {}
        if self.visibility:
            c = lora.Connector()
            properties.update({
                mapping.VISIBILITY: facet.get_one_class(c, self.visibility)
            })
        return properties

    def get_mo_address_and_properties(self):
        """
        Get a MO object fragment for the address, including any eventual
        properties

        Example::

          {
            'href': 'tel:+4512345678',
            'name': '+4512345678',
            'value': '12345678',
            'visibility': {
                'uuid': visibility
            }
          }
        """
        return {
            mapping.HREF: self.href,
            mapping.NAME: self.name,
            mapping.VALUE: self.value,
            **self._get_mo_properties()
        }


def get_handler_for_scope(scope: str) -> AddressHandler:
    handler = ADDRESS_HANDLERS.get(scope)
    if not handler:
        raise exceptions.ErrorCodes.E_INVALID_INPUT(
            'Invalid address scope type {}'.format(scope))
    return handler
