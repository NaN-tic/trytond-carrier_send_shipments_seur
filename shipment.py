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

logger = logging.getLogger(__name__)


class ShipmentOut:
    __metaclass__ = PoolMeta
    __name__ = 'stock.shipment.out'

    @classmethod
    def __setup__(cls):
        super(ShipmentOut, cls).__setup__()
        cls._error_messages.update({
            'seur_add_services': 'Select a service or default service in Seur API',
            'seur_not_country': 'Add country in shipment "%(name)s" delivery address',
            'seur_not_price': 'Shipment "%(name)s" not have price and send '
                'cashondelivery',
            'seur_error_zip': 'Seur not accept zip "%(zip)s"',
            'seur_not_send': 'Not send shipment %(name)s',
            'seur_not_send_error': 'Not send shipment %(name)s. %(error)s',
            'seur_not_label': 'Not available "%(name)s" label from Seur',
            })

    @staticmethod
    def seur_picking_data(api, shipment, service, price=None, weight=False):
        '''
        Seur Picking Data
        :param api: obj
        :param shipment: obj
        :param service: str
        :param price: string
        :param weight: bol
        Return data
        '''
        Uom = Pool().get('product.uom')

        if api.reference_origin and hasattr(shipment, 'origin'):
            code = shipment.origin and shipment.origin.rec_name or shipment.code
        else:
            code = shipment.code

        notes = ''
        if shipment.carrier_notes:
            notes = '%s\n' % shipment.carrier_notes

        packages = shipment.number_packages
        if not packages or packages == 0:
            packages = 1

        customer_city = unaccent(shipment.delivery_address.city)
        customer_zip = shipment.delivery_address.zip

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
        data['observaciones'] = notes
        data['referencia_expedicion'] = code
        data['ref_bulto'] = code
        data['clave_portes'] = 'F'
        if shipment.carrier_cashondelivery and price:
            data['clave_reembolso'] = 'F' # F: Facturacion
            data['valor_reembolso'] = str(price)
        else:
            data['clave_reembolso'] = ' '
            data['valor_reembolso'] = '0'

        if weight and hasattr(shipment, 'weight_func'):
            weight = shipment.weight_func
            if weight == 0:
                weight = 1
            if api.weight_api_unit:
                if shipment.weight_uom:
                    weight = Uom.compute_qty(
                        shipment.weight_uom, weight, api.weight_api_unit)
                elif api.weight_unit:
                    weight = Uom.compute_qty(
                        api.weight_unit, weight, api.weight_api_unit)
            data['total_kilos'] = str(weight)
            data['peso_bulto'] = str(weight)

        data['cliente_nombre'] = unaccent(shipment.customer.name)
        data['cliente_direccion'] = unaccent(shipment.delivery_address.street)
        #~ data['cliente_tipovia'] = 'CL'
        #~ data['cliente_tnumvia'] = 'N'
        #~ data['cliente_numvia'] = '93'
        #~ data['cliente_escalera'] = 'A'
        #~ data['cliente_piso'] = '3'
        #~ data['cliente_puerta'] = '2'
        data['cliente_poblacion'] = customer_city
        data['cliente_cpostal'] = customer_zip
        data['cliente_pais'] = shipment.delivery_address.country.code
        if shipment.customer.email:
            if shipment.delivery_address.email:
                data['cliente_email'] = shipment.delivery_address.email
            else:
                data['cliente_email'] = shipment.customer.email
        data['cliente_telefono'] = unspaces(shipment.get_phone_shipment_out(shipment))
        data['cliente_atencion'] = unaccent((shipment.delivery_address.name
                or shipment.customer.name))
        data['aviso_preaviso'] = 'S' if api.seur_aviso_preaviso else 'N'
        data['aviso_reparto'] = 'S' if api.seur_aviso_reparto else 'N'
        data['aviso_email'] = 'S' if api.seur_aviso_email else 'N'
        data['aviso_sms'] = 'S' if api.seur_aviso_sms else 'N'
        return data

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
        dbname = Transaction().database.name

        seur_context = {}
        if api.seur_pdf:
            seur_context['pdf'] = True
        with Picking(api.username, api.password, api.vat, api.seur_franchise, api.seur_seurid, \
                api.seur_ci, api.seur_ccc, seur_context) as picking_api:
            for shipment in shipments:
                service = shipment.carrier_service or shipment.carrier.service or default_service
                if not service:
                    message = self.raise_user_error('seur_add_services', {},
                        raise_exception=False)
                    errors.append(message)
                    continue

                if not shipment.delivery_address.country:
                    message = self.raise_user_error('seur_not_country', {},
                        raise_exception=False)
                    errors.append(message)
                    continue

                price = None
                if shipment.carrier_cashondelivery:
                    price = ShipmentOut.get_price_ondelivery_shipment_out(shipment)
                    if not price:
                        message = self.raise_user_error('seur_not_price', {
                                'name': shipment.rec_name,
                                }, raise_exception=False)
                        errors.append(message)
                        continue

                data = self.seur_picking_data(api, shipment, service, price, api.weight)
                reference, label, error = picking_api.create(data)

                if reference:
                    self.write([shipment], {
                        'carrier_tracking_ref': reference,
                        'carrier_service': service,
                        'carrier_delivery': True,
                        'carrier_send_date': ShipmentOut.get_carrier_date(),
                        'carrier_send_employee': ShipmentOut.get_carrier_employee() or None,
                        })
                    logger.info('Send shipment %s' % (shipment.code))
                    references.append(shipment.code)
                else:
                    logger.error('Not send shipment %s.' % (shipment.code))

                if label:
                    if api.seur_pdf:
                        with tempfile.NamedTemporaryFile(
                                prefix='%s-seur-%s-' % (dbname, reference),
                                suffix='.pdf', delete=False) as temp:
                            temp.write(decodestring(label))
                    else:
                        with tempfile.NamedTemporaryFile(
                                prefix='%s-seur-%s-' % (dbname, reference),
                                suffix='.zpl', delete=False) as temp:
                            temp.write(label.encode('utf-8'))
                    logger.info('Generated tmp label %s' % (temp.name))
                    temp.close()
                    labels.append(temp.name)
                else:
                    message = self.raise_user_error('seur_not_label', {
                            'name': shipment.rec_name,
                            }, raise_exception=False)
                    errors.append(message)
                    logger.error(message)

                if error:
                    message = self.raise_user_error('seur_not_send_error', {
                            'name': shipment.rec_name,
                            'error': error,
                            }, raise_exception=False)
                    logger.error(message)
                    errors.append(message)

        return references, labels, errors

    @classmethod
    def print_labels_seur(self, api, shipments):
        '''
        Get labels from shipments out from Seur
        Not available labels from Seur API. Not return labels
        '''
        pool = Pool()
        CarrierApi = pool.get('carrier.api')
        ShipmentOut = pool.get('stock.shipment.out')

        default_service = CarrierApi.get_default_carrier_service(api)
        dbname = Transaction().database.name

        labels = []
        errors = []

        seur_context = {}
        if api.seur_pdf:
            seur_context['pdf'] = True
        with Picking(api.username, api.password, api.vat, api.seur_franchise, api.seur_seurid, \
                api.seur_ci, api.seur_ccc, seur_context) as picking_api:
            for shipment in shipments:
                service = shipment.carrier_service or default_service
                if not service:
                    message = 'Add %s service or configure a default API Seur service.' % (shipment.code)
                    errors.append(message)
                    logger.error(message)
                    continue

                if not shipment.delivery_address.country:
                    message = 'Add %s a country.' % (shipment.code)
                    errors.append(message)
                    logger.error(message)
                    continue

                price = None
                if shipment.carrier_cashondelivery:
                    price = ShipmentOut.get_price_ondelivery_shipment_out(shipment)
                    if not price:
                        message = 'Shipment %s not have price and send ' \
                                'cashondelivery' % (shipment.code)
                        errors.append(message)
                        continue

                data = self.seur_picking_data(api, shipment, service, price, api.weight)
                label = picking_api.label(data)

                if label:
                    if api.seur_pdf:
                        with tempfile.NamedTemporaryFile(
                                prefix='%s-seur-%s-' % (dbname, shipment.carrier_tracking_ref),
                                suffix='.pdf', delete=False) as temp:
                            temp.write(decodestring(label.encode('utf-8')))
                    else:
                        with tempfile.NamedTemporaryFile(
                                prefix='%s-seur-%s-' % (dbname, shipment.carrier_tracking_ref),
                                suffix='.zpl', delete=False) as temp:
                            temp.write(label.encode('utf-8'))
                    logger.info(
                        'Generated tmp label %s' % (temp.name))
                    temp.close()
                    labels.append(temp.name)
                else:
                    message = 'Not label %s shipment available from Seur.' % (shipment.code)
                    errors.append(message)
                    logger.error(message)

        return labels
