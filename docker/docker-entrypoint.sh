#!/bin/sh

# Copyright (C) 2020 Magenta ApS, http://magenta.dk.
# Contact: info@magenta.dk.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

################################################################################
# Changes to this file requires approval from Labs. Please add a person from   #
# Labs as required approval to your MR if you have any changes.                #
################################################################################

set -e

python3 -m mora.cli initdb --wait 30
python3 -m mora.cli check-configuration-db-status
python3 -m mora.cli wait-for-rabbitmq --seconds 30

exec "$@"
