from odoo import models, fields, api
from odoo.exceptions import ValidationError








class SaleOrderlineTemplate(models.Model):
    _inherit = 'sale.order.line'


    x_price_subtotal = fields.Monetary(compute='_compute_amount', string='Subtotal', readonly=True, store=True)
 
 





    @api.depends('product_uom_qty', 'discount', 'price_unit', 'tax_id') 
    def _compute_amount(self):
        """
        Compute the amounts of the SO line.
        """
        for line in self:
            price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            taxes = line.tax_id.compute_all(price, line.order_id.currency_id, line.product_uom_qty, product=line.product_id, partner=line.order_id.partner_shipping_id)
            line.update({
                'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                'price_total': taxes['total_included'],
                'price_subtotal': taxes['total_excluded'],
                'x_price_subtotal': taxes['total_excluded'] + (line.price_unit * ((line.discount or 0.0) / 100.0) * line.product_uom_qty),
            })
            if self.env.context.get('import_file', False) and not self.env.user.user_has_groups('account.group_account_manager'):
                line.tax_id.invalidate_cache(['invoice_repartition_line_ids'], [line.tax_id.id])









class SaleOrderTemplate(models.Model):
    _inherit = 'sale.order'
    
    x_amount_untaxed = fields.Monetary(string='Untaxed Amount', store=True, readonly=True, compute='_amount_all', tracking=5)
    x_amount_untaxed_after_discount = fields.Monetary(string='Untaxed Amount After Discount', store=True, readonly=True, compute='_amount_all', tracking=5)
    x_total_discount = fields.Monetary(string='Total Discount', store=True, readonly=True, compute='_amount_all', tracking=5)

    @api.depends('order_line.price_total')
    def _amount_all(self):
        """
        Compute the total amounts of the SO.
        """
        for order in self:
            amount_untaxed = amount_tax = x_amount_untaxed = x_amount_untaxed_after_discount = x_total_discount = 0.0
            for line in order.order_line:
                amount_untaxed += line.price_subtotal
                x_amount_untaxed += line.x_price_subtotal
                x_total_discount += line.price_unit * ( (line.discount or 0.0) / 100.0) * line.product_uom_qty
                x_amount_untaxed_after_discount = x_amount_untaxed - x_total_discount
                amount_tax += line.price_tax
            order.update({
                'amount_untaxed': amount_untaxed,
                'x_amount_untaxed': x_amount_untaxed,
                'amount_tax': amount_tax,
                'x_amount_untaxed_after_discount': x_amount_untaxed_after_discount,
                'x_total_discount': x_total_discount,
                'amount_total': amount_untaxed + amount_tax,
            })