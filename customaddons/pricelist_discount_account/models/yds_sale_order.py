from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError

# sale.order -- sale.order.line

class YDSSaleOrder(models.Model):
    _inherit = "sale.order"

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

    #fixed double id  issues
    @api.onchange('order_line')
    def rename_line(self):
        print("rename_lines")
        productNames = [] 
        productCounts = [] 
        for rec in self :
            innerloopCount=0
            for line in rec.order_line:
                print("line number: " + str(innerloopCount))
                innerloopCount+=1
                print(line.product_id.name)
                if line.product_id.name in productNames:
                    print("product found") 
                    index = productNames.index(line.product_id.name)
                    productCounts[index]+=1
                    line.name = line.product_id.name +" ("+str(productCounts[index])+")"
                    print(line.name) 
                else:   
                    print("product not found..adding new product")
                    productNames.append(line.product_id.name)
                    productCounts.append(1)
                    print(productNames)
                    print(productCounts)
    # Send values to account.move
    def _prepare_invoice(self):
        res = super(YDSSaleOrder, self)._prepare_invoice()
        for rec in self:
            res['yds_pricelist_name'] = rec.pricelist_id.name
            res['yds_pricelist_account_id'] = rec.pricelist_id.yds_assigned_discount_account
            
            res['yds_amount_untaxed'] = rec.x_amount_untaxed
            res['yds_amount_untaxed_after_discount'] = rec.x_amount_untaxed_after_discount
            res['yds_is_sales_order'] = True

            
        return res


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


