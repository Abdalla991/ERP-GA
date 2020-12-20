# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError


class KsGlobalDiscountSales(models.Model):
    _inherit = "sale.order"

    ks_global_discount_type = fields.Selection([('percent', 'Percentage')],
                                               string='Universal Discount Type', readonly=True,
                                               default='percent')
    ks_global_discount_rate = fields.Float('Universal Discount',
                                           readonly=True,
                                           states={'draft': [('readonly', False)], 'sent': [('readonly', False)]})
    ks_amount_discount = fields.Monetary(string='Universal Discount', readonly=True, compute='_amount_all', store=True,
                                         track_visibility='always')
    ks_enable_discount = fields.Boolean(compute='ks_verify_discount')

    @api.depends('company_id.ks_enable_discount')
    def ks_verify_discount(self):
        for rec in self:
            rec.ks_enable_discount = rec.company_id.ks_enable_discount

    @api.depends('order_line.price_total', 'ks_global_discount_rate')
    def _amount_all(self):
        res = super(KsGlobalDiscountSales, self)._amount_all()
        for rec in self:
            if not ('ks_global_tax_rate' in rec):
                rec.ks_calculate_discount()
        return res

    @api.onchange('partner_id')
    def calc_uni_rate(self):
        for rec in self:
            rec.ks_global_discount_rate = rec.partner_id.yds_customer_universal_discount_rate

    # @api.multi
    def _prepare_invoice(self):
        res = super(KsGlobalDiscountSales, self)._prepare_invoice()
        for rec in self:
            res['ks_global_discount_rate'] = rec.ks_global_discount_rate
            res['ks_global_discount_type'] = rec.ks_global_discount_type
            
        return res

    # @api.multi
    def ks_calculate_discount(self):
        for rec in self:
            if rec.ks_global_discount_type == "amount":
                rec.ks_amount_discount = rec.ks_global_discount_rate if rec.amount_untaxed > 0 else 0

            elif rec.ks_global_discount_type == "percent":
                if rec.ks_global_discount_rate != 0.0:
                    rec.ks_amount_discount = (rec.amount_untaxed) * rec.ks_global_discount_rate / 100
                else:
                    rec.ks_amount_discount = 0
            elif not rec.ks_global_discount_type:
                rec.ks_amount_discount = 0
                rec.ks_global_discount_rate = 0
            rec.amount_tax = rec.amount_tax * (1-rec.ks_global_discount_rate/100)
            rec.amount_total = rec.amount_untaxed + rec.amount_tax - rec.ks_amount_discount
            # rec.amount_untaxed -= rec.ks_amount_discount

    @api.constrains('ks_global_discount_rate')
    def ks_check_discount_value(self):
        if self.ks_global_discount_type == "percent":
            if self.ks_global_discount_rate > 100 or self.ks_global_discount_rate < 0:
                raise ValidationError('You cannot enter percentage value greater than 100.')
        else:
            if self.ks_global_discount_rate < 0 or self.ks_global_discount_rate > self.amount_untaxed:
                raise ValidationError(
                    'You cannot enter discount amount greater than actual cost or value lower than 0.')


    # def _amount_by_group(self):
    #     for order in self:
    #         currency = order.currency_id or order.company_id.currency_id
    #         fmt = partial(formatLang, self.with_context(lang=order.partner_id.lang).env, currency_obj=currency)
    #         res = {}
    #         for line in order.order_line:
    #             price_reduce = line.price_unit * (1.0 - line.discount / 100.0)
    #             taxes = line.tax_id.compute_all(price_reduce, quantity=line.product_uom_qty, product=line.product_id, partner=order.partner_shipping_id)['taxes']
    #             for tax in line.tax_id:
    #                 group = tax.tax_group_id
    #                 res.setdefault(group, {'amount': 0.0, 'base': 0.0})
    #                 for t in taxes:
    #                     if t['id'] == tax.id or t['id'] in tax.children_tax_ids.ids:
    #                         res[group]['amount'] += t['amount']
    #                         res[group]['base'] += t['base']
    #         res[group]['amount'] -= order.ks_amount_discount
    #         res[group]['base'] -= order.ks_amount_discount
    #         res = sorted(res.items(), key=lambda l: l[0].sequence)
    #         order.amount_by_group = [(
    #             l[0].name, l[1]['amount'], l[1]['base'],
    #             fmt(l[1]['amount']), fmt(l[1]['base']),
    #             len(res),
    #         ) for l in res]

class KsSaleAdvancePaymentInv(models.TransientModel):
    _inherit = "sale.advance.payment.inv"

    def _create_invoice(self, order, so_line, amount):
        invoice = super(KsSaleAdvancePaymentInv, self)._create_invoice(order, so_line, amount)
        if invoice:
            invoice['ks_global_discount_rate'] = order.ks_global_discount_rate
            invoice['ks_global_discount_type'] = order.ks_global_discount_type
        return invoice
