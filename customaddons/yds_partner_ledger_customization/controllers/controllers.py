# -*- coding: utf-8 -*-
# from odoo import http


# class YdsPartnerLedgerCustomization(http.Controller):
#     @http.route('/yds_partner_ledger_customization/yds_partner_ledger_customization/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/yds_partner_ledger_customization/yds_partner_ledger_customization/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('yds_partner_ledger_customization.listing', {
#             'root': '/yds_partner_ledger_customization/yds_partner_ledger_customization',
#             'objects': http.request.env['yds_partner_ledger_customization.yds_partner_ledger_customization'].search([]),
#         })

#     @http.route('/yds_partner_ledger_customization/yds_partner_ledger_customization/objects/<model("yds_partner_ledger_customization.yds_partner_ledger_customization"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('yds_partner_ledger_customization.object', {
#             'object': obj
#         })
