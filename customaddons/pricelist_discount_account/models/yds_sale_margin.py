# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models

class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    yds_margin = fields.Float(
        "Margin", compute='_compute_yds_margin',
        digits='Product Price', store=True, groups="base.group_user")
    yds_margin_percent = fields.Float(
        "Margin (%)", compute='_compute_yds_margin', store=True, groups="base.group_user")
    purchase_price = fields.Float(
        string='Cost', compute="_compute_purchase_price",
        digits='Product Price', store=True, readonly=False,
        groups="base.group_user")

    @api.depends('product_id', 'company_id', 'currency_id', 'product_uom')
    def _compute_purchase_price(self):
        for line in self:
            if not line.product_id:
                line.purchase_price = 0.0
                continue
            line = line.with_company(line.company_id)
            product = line.product_id
            product_cost = product.standard_price
            if not product_cost:
                # If the standard_price is 0
                # Avoid unnecessary computations
                # and currency conversions
                line.purchase_price = 0.0
                continue
            fro_cur = product.cost_currency_id
            to_cur = line.currency_id or line.order_id.currency_id
            if line.product_uom and line.product_uom != product.uom_id:
                product_cost = product.uom_id._compute_price(
                    product_cost,
                    line.product_uom,
                )
            line.purchase_price = fro_cur._convert(
                from_amount=product_cost,
                to_currency=to_cur,
                company=line.company_id or self.env.company,
                date=line.order_id.date_order or fields.Date.today(),
                round=False,
            ) if to_cur and product_cost else product_cost
            # The pricelist may not have been set, therefore no conversion
            # is needed because we don't know the target currency..

    @api.depends('x_price_subtotal_wo_uni', 'product_uom_qty', 'purchase_price')
    def _compute_yds_margin(self):
        for line in self:
            sale_price=  line.x_price_subtotal
            line.yds_margin =  sale_price - (line.purchase_price * line.product_uom_qty)

            print(str(line.purchase_price))
            print(str(line.product_uom_qty))
            print(str(line.yds_margin))
            line.yds_margin_percent = sale_price and line.yds_margin/sale_price

class SaleOrder(models.Model):
    _inherit = "sale.order"

    yds_margin = fields.Monetary("Margin", compute='_compute_yds_margin', store=True)
    yds_margin_percent = fields.Float("Margin (%)", compute='_compute_yds_margin', store=True)

    @api.depends('order_line.yds_margin', 'amount_untaxed')
    def _compute_yds_margin(self):
        if not all(self._ids):
            for order in self:
                order.yds_margin = sum(order.order_line.mapped('yds_margin'))
                order.yds_margin_percent = order.amount_untaxed and order.yds_margin/order.amount_untaxed
        else:
            self.env["sale.order.line"].flush(['yds_margin'])
            # On batch records recomputation (e.g. at install), compute the margins
            # with a single read_group query for better performance.
            # This isn't done in an onchange environment because (part of) the data
            # may not be stored in database (new records or unsaved modifications).
            grouped_order_lines_data = self.env['sale.order.line'].read_group(
                [
                    ('order_id', 'in', self.ids),
                ], ['yds_margin', 'order_id'], ['order_id'])
            mapped_data = {m['order_id'][0]: m['yds_margin'] for m in grouped_order_lines_data}
            for order in self:
                order.yds_margin = mapped_data.get(order.id, 0.0)
                order.yds_margin_percent = order.amount_untaxed and order.yds_margin/order.amount_untaxed

class SaleReport(models.Model):
    _inherit = 'sale.report'

    margin = fields.Float('Margin')

    def _query(self, with_clause='', fields={}, groupby='', from_clause=''):
        fields['margin'] = ", SUM(l.yds_margin / CASE COALESCE(s.currency_rate, 0) WHEN 0 THEN 1.0 ELSE s.currency_rate END) AS margin"
        return super(SaleReport, self)._query(with_clause, fields, groupby, from_clause)
