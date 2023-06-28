#!/usr/bin/env bash

set -e

if [[ -z "${WITH_LOGFILE}" ]] ; then
  sed -i '/logfile[[:space:]]*=/d' "${ODOO_RC}"
fi

if [[ "$1" == "runbot" ]] ; then
  shift
  wait-for-sql
  exec ~/instance/odoo/odoo-bin -i runbot_travis2docker --without-demo=all "$@"
else
  exec "$@"
fi
