# This file is part of carrier_send_shipments_seur module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from seur import Picking
from trytond.pool import PoolMeta
from trytond.transaction import Transaction
from base64 import decodestring

__all__ = ['CarrierManifest']
__metaclass__ = PoolMeta


class CarrierManifest:
    __name__ = 'carrier.manifest'

    def get_manifest_seur(self, api, from_date, to_date):
        dbname = Transaction().database.name

        context = {}
        with Picking(api.username, api.password, api.vat, api.seur_franchise,
                api.seur_seurid, api.seur_ci, api.seur_ccc,
                context) as picking_api:
            data = {}
            data['date'] = '%s-%s-%s' % (
                from_date.year,
                from_date.strftime('%m'),
                from_date.strftime('%d'),
                )
            manifest_file = picking_api.manifiesto(data)

        if manifest_file:
            manifiest = decodestring(manifest_file)
            file_name = '%s-manifest-seur.pdf' % dbname
            return (manifiest, file_name)
        else:
            return
