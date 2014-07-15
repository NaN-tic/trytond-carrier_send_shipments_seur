# This file is part of the carrier_send_shipments module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from trytond.pool import Pool, PoolMeta
from trytond.transaction import Transaction
from seur.picking import Picking
from trytond.modules.carrier_send_shipments.tools import unaccent, unspaces
from base64 import decodestring
import logging
import tempfile

__all__ = ['ShipmentOut']
__metaclass__ = PoolMeta


class ShipmentOut:
    __name__ = 'stock.shipment.out'

    @classmethod
    def send_seur(self, api, shipments):
        '''
        Send shipments out to seur
        :param api: obj
        :param shipments: list
        Return references, labels, errors
        '''
        pool = Pool()
        CarrierApi = pool.get('carrier.api')
        ShipmentOut = pool.get('stock.shipment.out')

        references = []
        labels = []
        errors = []

        default_service = CarrierApi.get_default_carrier_service(api)
        dbname = Transaction().cursor.dbname

        seur_context = {}
        if api.seur_pdf:
            seur_context['pdf'] = True
        with Picking(api.username, api.password, api.vat, api.seur_franchise, api.seur_seurid, \
                api.seur_ci, api.seur_ccc, seur_context) as picking_api:
            for shipment in shipments:
                service = shipment.carrier_service or default_service

                notes = ''
                if shipment.carrier_notes:
                    notes = shipment.carrier_notes

                packages = shipment.number_packages
                if packages == 0:
                    packages = 1

                customer_city = unaccent(shipment.delivery_address.city)
                customer_zip = shipment.delivery_address.zip

                # change customer city to seur city because seur required
                # city equal in their API
                seur_customer_city = customer_city
                seur_cities = picking_api.zip(customer_zip)
                if seur_cities:
                    seur_customer_city = seur_cities[0]['NOM_POBLACION']
                for option in seur_cities:
                    if option['NOM_POBLACION'] == customer_city.upper():
                        seur_customer_city = option['NOM_POBLACION']
                        break

                notes = '%(notes)s' \
                    '%(name)s. %(street)s. %(zip)s %(city)s - %(country)s\n' % {
                        'notes': unaccent(notes),
                        'name': unaccent(shipment.customer.name),
                        'street': unaccent(shipment.delivery_address.street),
                        'zip': customer_zip,
                        'city': customer_city,
                        'country': shipment.delivery_address.country.code,
                        }

                data = {}
                data['servicio'] = str(service.code)
                data['product'] = '2'
                data['total_bultos'] = packages
                if api.weight and getattr(shipment, 'weight_func'):
                    data['total_kilos'] = str(shipment.weight_func)
                data['observaciones'] = notes
                data['referencia_expedicion'] = shipment.code
                data['ref_bulto'] = shipment.code
                data['clave_portes'] = 'F'
                if shipment.carrier_cashondelivery:
                    price_ondelivery = ShipmentOut.get_price_ondelivery_shipment_out(shipment)
                    if not price_ondelivery:
                        message = 'Shipment %s not have price and send ' \
                                'cashondelivery' % (shipment.code)
                        errors.append(message)
                        continue
                    data['clave_reembolso'] = 'F' # F: Facturacion
                    data['valor_reembolso'] = str(price_ondelivery)
                else:
                    data['clave_reembolso'] = ' '
                    data['valor_reembolso'] = '0'
                if api.weight and getattr(shipment, 'weight_func'):
                    weight = str(shipment.weight_func)
                    data['total_kilos'] = weight
                    data['peso_bulto'] = weight
                data['cliente_nombre'] = unaccent(shipment.customer.name)
                data['cliente_direccion'] = unaccent(shipment.delivery_address.street)
                #~ data['cliente_tipovia'] = 'CL'
                #~ data['cliente_tnumvia'] = 'N'
                #~ data['cliente_numvia'] = '93'
                #~ data['cliente_escalera'] = 'A'
                #~ data['cliente_piso'] = '3'
                #~ data['cliente_puerta'] = '2'
                data['cliente_poblacion'] = seur_customer_city
                data['cliente_cpostal'] = customer_zip
                data['cliente_pais'] = shipment.delivery_address.country.code
                if shipment.customer.email:
                    if shipment.delivery_address.email:
                        data['cliente_email'] = shipment.delivery_address.email
                    else:
                        data['cliente_email'] = shipment.customer.email
                data['cliente_telefono'] = unspaces(ShipmentOut.get_phone_shipment_out(shipment))
                data['cliente_atencion'] = unaccent((shipment.delivery_address.name
                        or shipment.customer.name))

                # Send picking data to carrier
                reference, label, error = picking_api.create(data)

                if reference:
                    self.write([shipment], {
                        'carrier_tracking_ref': reference,
                        'carrier_service': service,
                        'carrier_delivery': True,
                        'carrier_send_date': ShipmentOut.get_carrier_date(),
                        'carrier_send_employee': ShipmentOut.get_carrier_employee() or None,
                        })
                    logging.getLogger('seur').info(
                        'Send shipment %s' % (shipment.code))
                    references.append(shipment.code)
                else:
                    logging.getLogger('seur').error(
                        'Not send shipment %s.' % (shipment.code))

                if label:
                    if api.seur_pdf:
                        with tempfile.NamedTemporaryFile(
                                prefix='%s-seur-%s-' % (dbname, reference),
                                suffix='.pdf', delete=False) as temp:
                            temp.write(decodestring(label))
                    else:
                        with tempfile.NamedTemporaryFile(
                                prefix='%s-seur-%s-' % (dbname, reference),
                                suffix='.txt', delete=False) as temp:
                            temp.write(label)
                    logging.getLogger('seur').info(
                        'Generated tmp label %s' % (temp.name))
                    temp.close()
                    labels.append(temp.name)
                else:
                    message = 'Not label %s shipment available from Seur.' % (shipment.code)
                    errors.append(message)
                    logging.getLogger('seur').error(message)

                if error:
                    logging.getLogger('seur').error(
                        'Not send shipment %s. %s' % (shipment.code, error))
                    errors.append(shipment.code)

        return references, labels, errors

    @classmethod
    def print_labels_seur(cls, api, shipments):
        '''
        Get labels from shipments out from Seur
        Not available labels from Seur API. Not return labels
        '''
        labels = []
        return labels
