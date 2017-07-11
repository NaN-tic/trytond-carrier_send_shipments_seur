# This file is part of the carrier_send_shipments_seur module for Tryton.
# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from email import Utils
from email import Encoders
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from trytond.model import ModelSQL, ModelView, fields
from trytond.wizard import Wizard, StateView, StateTransition, Button
from trytond.pool import Pool, PoolMeta
from trytond.transaction import Transaction
from trytond.pyson import Eval, Not, Equal, Bool
from trytond.modules.carrier_send_shipments_seur.tools import seurbarcode
import logging
import datetime
import genshi
import os
import codecs

try:
    from seur.picking import *
except ImportError:
    logger = logging.getLogger(__name__)
    message = 'Install Seur: pip install seur'
    logger.error(message)
    raise Exception(message)

__all__ = ['CarrierApi', 'CarrierApiSeurOffline',
    'CarrierApiSeurOfflineSendStart', 'CarrierApiSeurOfflineSend',
    'CarrierApiSeurZip', 'LoadCarrierApiSeurZipStart', 'LoadCarrierApiSeurZip']
__metaclass__ = PoolMeta

logger = logging.getLogger(__name__)
offline_loader = genshi.template.TemplateLoader(
    os.path.join(os.path.dirname(__file__), 'template'),
    auto_reload=True)


class CarrierApi:
    __name__ = 'carrier.api'
    seur_offline = fields.Boolean('Offline',
        help='Working the API offline')
    seur_franchise = fields.Char('Franchise', states={
            'required': Eval('method') == 'seur',
        }, depends=['method'],
        help='Seur Franchise code')
    seur_seurid = fields.Char('ID', states={
            'required': Eval('method') == 'seur',
        }, depends=['method'],
        help='Seur Description code')
    seur_ci = fields.Char('CI', states={
            'required': Eval('method') == 'seur',
        }, depends=['method'],
        help='Seur Customer Code (ci)')
    seur_ccc = fields.Char('CCC', states={
            'required': Eval('method') == 'seur',
        }, depends=['method'],
        help='Seur Account Code (ccc)')
    seur_printer = fields.Char('Printer', help='Seur Printer')
    seur_printer_model = fields.Char('Printer Model', help='Seur Printer Model')
    seur_ecb_code = fields.Char('ECB Code', help='Seur ECB Code')
    seur_pdf = fields.Boolean('PDF', help='PDF Label')
    seur_aviso_preaviso = fields.Boolean('Aviso Preaviso')
    seur_aviso_reparto = fields.Boolean('Aviso Reparto')
    seur_aviso_email = fields.Boolean('Aviso Email')
    seur_aviso_sms = fields.Boolean('Aviso SMS')
    seur_reference = fields.Many2One('ir.sequence', 'Seur Reference', states={
            'invisible': ~Bool(Eval('seur_offline')),
            'required': Bool(Eval('seur_offline')),
        }, domain=[
            ('code', '=', 'carrier.api.seur'),
        ], depends=['seur_offline'],
        help='Sequence to assign a tracking reference')
    seur_minimum_reference = fields.Integer('Min Reference', states={
            'invisible': ~Bool(Eval('seur_offline')),
            'required': Bool(Eval('seur_offline')),
        }, depends=['seur_offline'],
        help='Minimum number reference')
    seur_maximun_reference = fields.Integer('Max Reference', states={
            'invisible': ~Bool(Eval('seur_offline')),
            'required': Bool(Eval('seur_offline')),
        }, depends=['seur_offline'],
        help='Maximun number reference')
    seur_email = fields.Char('Seur Email', states={
            'invisible': ~Bool(Eval('seur_offline')),
            'required': Bool(Eval('seur_offline')),
        }, depends=['seur_offline'],
        help='Seur TO email')
    seur_email_backup = fields.Char('Seur Backup Email', states={
            'invisible': ~Bool(Eval('seur_offline')),
        }, depends=['seur_offline'],
        help='Seur CC backup email')
    seur_filename = fields.Char('Seur Filename', states={
            'invisible': ~Bool(Eval('seur_offline')),
            'required': Bool(Eval('seur_offline')),
        }, depends=['seur_offline'],
        help='Prefix Seur Filename')

    @classmethod
    def __setup__(cls):
        super(CarrierApi, cls).__setup__()
        cls._error_messages.update({
            'working_offline': 'Can not test connection because are working '
                'offline',
            })

    @classmethod
    def get_carrier_app(cls):
        '''
        Add Carrier Seur APP
        '''
        res = super(CarrierApi, cls).get_carrier_app()
        res.append(('seur', 'Seur'))
        return res

    @classmethod
    def view_attributes(cls):
        return super(CarrierApi, cls).view_attributes() + [
            ('//page[@id="seur"]', 'states', {
                    'invisible': Not(Equal(Eval('method'), 'seur')),
                    })]

    @classmethod
    def test_seur(cls, api):
        'Test Seur connection'
        message = 'Connection unknown result'

        if api.seur_offline:
            cls.raise_user_error('working_offline')

        seur_context = {}
        with API(api.username, api.password, api.vat, api.seur_franchise, api.seur_seurid, \
                api.seur_ci, api.seur_ccc, seur_context) as seur_api:
            message = seur_api.test_connection()
        cls.raise_user_error(message)


class CarrierApiSeurOffline(ModelSQL, ModelView):
    'Carrier API Seur Offline'
    __name__ = 'carrier.api.seur.offline'
    _rec_name = 'shipment'
    company = fields.Many2One('company.company', 'Company', required=True)
    api = fields.Many2One('carrier.api', 'API', required=True,
        states={
            'readonly': Eval('state') != 'draft',
        }, depends=['state'])
    shipment = fields.Many2One('stock.shipment.out', 'Shipment', required=True,
        domain=[
            ('state', 'in', ['packed', 'done']),
            ],
        states={
            'readonly': Eval('state') != 'draft',
        }, depends=['state'])
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done'),
        ], 'State', readonly=True)

    @classmethod
    def __setup__(cls):
        super(CarrierApiSeurOffline, cls).__setup__()
        cls._order.insert(0, ('id', 'DESC'))
        cls._error_messages.update({
            'no_smtp_seur': 'Not found SMTP server. '
                'Configure a SMTP server related with Seur Offline!',
            'smtp_seur_error':
                'Wrong connection to SMTP server. Not send email.',
            'error_smtp': 'Error SMTP connection. Try again.',
            })

    @staticmethod
    def default_company():
        return Transaction().context.get('company')

    @staticmethod
    def default_state():
        return 'draft'

    @classmethod
    def send_seur_offline(cls):
        API = Pool().get('carrier.api')

        for api in API.search([
                ('method', '=', 'seur'),
                ('seur_offline', '=', True),
                ]):
            cls.send_seur_shipments(api)

    @classmethod
    def send_seur_shipments(cls, api):
        pool = Pool()
        SMTP = pool.get('smtp.server')
        ShipmentOut = pool.get('stock.shipment.out')
        CarrierApi = pool.get('carrier.api')

        server = SMTP.get_smtp_server_from_model(cls.__name__)
        if not server:
            cls.raise_user_error('no_smtp_seur')

        seur_shipments = cls.search([
            ('api', '=', api),
            ('state', '=', 'draft'),
            ])
        if not seur_shipments:
            return

        default_service = CarrierApi.get_default_carrier_service(api)

        shipments_data = []
        for s in seur_shipments:
            shipment = s.shipment

            if not shipment.carrier_tracking_ref:
                logger.error('It is missing the tracking ref in shipment "%s"' % (
                    shipment.rec_name))
                continue

            if shipment.warehouse.address:
                waddress = shipment.warehouse.address
            else:
                waddress = api.company.party.addresses[0]
            from_zip = waddress.zip

            price = None
            if shipment.carrier_cashondelivery:
                price = ShipmentOut.get_price_ondelivery_shipment_out(shipment)

            service = shipment.carrier_service or shipment.carrier.service \
                or default_service

            vals = ShipmentOut.seur_picking_data(api, shipment, service, price,
                api.weight)

            barcodes = []
            barcodes_compact = []
            for seur_reference in shipment.carrier_tracking_ref.split(','):
                barcode = seurbarcode(
                    from_zip=from_zip,
                    to_zip=vals['cliente_cpostal'],
                    reference=seur_reference,
                    transport=1) # TODO transport type is fixed to 1
                barcodes.append(barcode)
                barcodes_compact.append(barcode.replace (' ', ''))
            vals['barcodes'] = barcodes
            vals['barcodes_compact'] = barcodes_compact
            # add shipment to send to seur
            shipments_data.append(vals)

        vals = {}
        vals['ci'] = api.seur_ci
        vals['vat'] = api.vat
        vals['ccc'] = api.seur_ccc
        vals['shipments'] = shipments_data
        tmpl = offline_loader.load('offline-send.xml')
        xml = tmpl.generate(**vals).render()

        # TODO two-phase commit protocol
        # https://bugs.tryton.org/issue3553

        from_ = server.smtp_email
        recipients = [api.seur_email]
        filename = '%s_%s.txt' % (api.seur_filename, datetime.datetime.now().strftime("%d%m%Y%H%M"))
        subject = '%s - %s - %s' % (api.seur_seurid, api.seur_ccc, filename)

        msg = MIMEMultipart()
        msg['Subject'] = Header(subject, 'utf-8')
        msg['From'] = from_
        msg['To'] = ', '.join(recipients)
        msg['Reply-to'] = server.smtp_email
        # msg['Date']     = Utils.formatdate(localtime = 1)
        msg['Message-ID'] = Utils.make_msgid()

        attach = MIMEBase('application', "octet-stream")
        attach.set_payload(xml)
        Encoders.encode_base64(attach)
        attach.add_header('Content-Disposition',
            'attachment; filename="%s"' % filename)
        msg.attach(attach)

        try:
            smtp_server = server.get_smtp_server()
            smtp_server.sendmail(from_, recipients, msg.as_string())
            smtp_server.quit()
            cls.write(seur_shipments, {'state': 'done'})
            logger.info('Send Seur Offline: %s' % (filename))
        except:
            cls.raise_user_error('error_smtp')
            logger.error('Send Seur Offline: %s' % (filename))


class CarrierApiSeurOfflineSendStart(ModelView):
    'Carrier API Seur Offline Send Start'
    __name__ = 'carrier.api.seur.offline.send.start'
    api = fields.Many2One('carrier.api', 'API', required=True,
        domain=[('method', '=', 'seur')])


class CarrierApiSeurOfflineSend(Wizard):
    'Carrier API Seur Offile Send'
    __name__ = 'carrier.api.seur.offline.send'

    start = StateView('carrier.api.seur.offline.send.start',
        'carrier_send_shipments_seur.carrier_send_shipments_seur_send_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Send', 'send', 'tryton-ok', default=True),
            ])
    send = StateTransition()

    def transition_send(self):
        Offline = Pool().get('carrier.api.seur.offline')

        api = self.start.api
        Offline.send_seur_shipments(api)
        return 'end'


class CarrierApiSeurZip(ModelSQL, ModelView):
    'Carrier API Seur Zip'
    __name__ = 'carrier.api.seur.zip'
    codpos_zip = fields.Char('CodPos Zip')
    codpos_city = fields.Char('CodPos City')
    codpos_country = fields.Char('CodPos Country')
    codpos_code = fields.Char('CodPos Code')
    coddest_code = fields.Char('CodDest Code')
    coddest_name = fields.Char('CodDest Name')


class LoadCarrierApiSeurZipStart(ModelView):
    'Load Carrier API Seur Zip Start'
    __name__ = 'carrier.api.seur.zip.load.start'


class LoadCarrierApiSeurZip(Wizard):
    'Load Carrier API Seur Zip Start'
    __name__ = 'carrier.api.seur.zip.load'

    start = StateView('load.banks.start',
        'carrier_send_shipments_seur.carrier_api_seur_load_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Accept', 'accept', 'tryton-ok', default=True),
            ])
    accept = StateTransition()

    def transition_accept(self):
        SeurZip = Pool().get('carrier.api.seur.zip')

        zips = SeurZip.search([])
        if zips:
            SeurZip.delete(zips)

        fcodpos = os.path.join(os.path.dirname(__file__), 'seur-codpos.txt')
        fcoddest = os.path.join(os.path.dirname(__file__), 'seur-coddest.txt')

        # codpos:
        # 0008733EL PLA DEL PENEDES       ES0930
        # codpos_zip:08733
        # codpos_city: EL PLA DEL PENEDESq
        # codpos_country: ES
        # codpos_code: 930

        # coddest:
        # 0930002001BCN-PENEDES       1
        # coddest_code: 930
        # coddest_name: BCN-PENEDES

        codpos = {}
        with codecs.open(fcodpos, 'r', 'UTF-8') as f:
            for line in f:
                codpos_code = u'%s' % line[35:38]
                vals = {
                    'codpos_zip': u'%s' % line[2:7],
                    'codpos_city': u'%s' % line[7:32].rstrip(),
                    'codpos_country': u'%s' % line[32:34],
                    'codpos_code': codpos_code,
                    }
                if codpos_code in codpos:
                    codpos[codpos_code].append(vals)
                else:
                    codpos[codpos_code] = [vals]

        with codecs.open(fcoddest, 'r', 'UTF-8') as f:
            for line in f:
                coddest_code = u'%s' % line[1:4]
                if coddest_code in codpos:
                    for z in codpos[coddest_code]:
                        z['coddest_code'] = coddest_code
                        z['coddest_name'] = u'%s' % line[10:28].rstrip()

        to_create = []
        for _, v in codpos.iteritems():
            to_create += v

        if to_create:
            SeurZip.create(to_create)

        return 'end'
