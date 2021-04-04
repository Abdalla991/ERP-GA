from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

# sale.order -- sale.order.line


class YDSSaleOrder(models.Model):
    _inherit = "sale.order"

    x_amount_untaxed = fields.Monetary(
        string='Untaxed Amount', store=True, readonly=True, compute='_amount_all', tracking=5)
    x_amount_untaxed_after_discount = fields.Monetary(
        string='Untaxed Amount After Discount', store=True, readonly=True, compute='_amount_all', tracking=5)
    x_amount_untaxed_after_uni_discount = fields.Monetary(
        string='Untaxed Amount After Universal Discount', store=True, readonly=True, compute='_amount_all', tracking=5)
    
        
    x_total_discount = fields.Monetary(
        string='Total Discount', store=True, readonly=True, compute='_amount_all', tracking=5)
    yds_customer_tag = fields.Char(

        'Customer Tags', compute='_compute_yds_customer_tags', store=True, readonly=True)
    
    @api.depends('partner_id')
    def _compute_yds_customer_tags(self):
        for record in self:
            record.yds_customer_tag = record.partner_id.category_id.name

    @api.depends('order_line.price_total')
    def _amount_all(self):
        """
        Compute the total amounts of the SO.
        """
        for order in self:
            amount_untaxed = amount_tax = x_amount_untaxed = x_amount_untaxed_after_discount = x_total_discount = 0.0
            for line in order.order_line:
                amount_untaxed += line.price_subtotal
                x_amount_untaxed += line.x_price_subtotal_wo_uni
                x_total_discount += line.price_unit * \
                    ((line.discount or 0.0) / 100.0) * line.product_uom_qty
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

    # fixed double id  issues
    # @api.onchange('order_line')

    def rename_line(self):
        print("rename_lines")
        productNames = []
        productCounts = []
        for rec in self:
            innerloopCount = 0
            for line in rec.order_line:
                print("line number: " + str(innerloopCount))
                innerloopCount += 1
                print(line.product_id.name)
                if line.product_id.name in productNames:
                    print("product found")
                    index = productNames.index(line.product_id.name)
                    productCounts[index] += 1
                    line.name = line.product_id.name + \
                        " ("+str(productCounts[index])+")"
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

        # @api.model
        # def fields_get(self, fields=None):
        #     # Fields to be added in Filters/Group By
        #     show = ['yds_customer_tag']
        #     res = super(YDSSaleReport, self).fields_get()
        #     # True = add fields, False = Remove fields
        #     for field in show:
        #         res[field]['selectable'] = True
        #         res[field]['sortable'] = True
        #     return res


class SaleOrderlineTemplate(models.Model):
    _inherit = 'sale.order.line'

    x_price_subtotal = fields.Monetary(
        compute='_compute_amount', string='Subtotal', readonly=True, store=True)
    x_price_total = fields.Monetary(
        compute='_compute_amount', string='Total', readonly=True, store=True)
    x_price_subtotal_wo_uni = fields.Monetary(
        compute='_compute_amount', string='Subtotal', readonly=True, store=True)
    x_price_total_wo_uni = fields.Monetary(
        compute='_compute_amount', string='Total', readonly=True, store=True)

    # yds_untaxed_amount_invoiced = fields.Monetary(
    #     "Untaxed Invoiced Amount", compute='_compute_yds_untaxed_amount_invoiced', compute_sudo=True, store=True)
    # yds_untaxed_amount_to_invoice = fields.Monetary(
    #     "Untaxed Amount To Invoice", compute='_compute_yds_untaxed_amount_to_invoice', compute_sudo=True, store=True)
    yds_cost_percentage = fields.Float(
        'Cost %', compute='_compute_yds_cost_percentage', store=True, readonly=True)
    yds_product_cost = fields.Float(
        'Cost ', compute='_compute_yds_product_cost', store=True, readonly=True)



    @api.depends('price_unit', 'product_id')
    def _compute_yds_cost_percentage(self):
        for line in self:
            product = line.product_id
            product_cost = product.standard_price
            if (line.price_unit > 0):
                line.yds_cost_percentage = (product_cost / line.price_unit)*100

    @api.depends('product_id')
    def _compute_yds_product_cost(self):
        for line in self:
            line.yds_product_cost = line.product_id.standard_price * line.product_uom_qty

    # @api.depends('invoice_lines', 'invoice_lines.price_total', 'invoice_lines.move_id.state', 'invoice_lines.move_id.move_type','untaxed_amount_invoiced')
    # def _compute_yds_untaxed_amount_invoiced(self):
    #     print("editing untaxted_amount_invoiced")
    #     for line in self:
    #         if line.untaxed_amount_invoiced !=0:
    #             line.yds_untaxed_amount_invoiced = line.untaxed_amount_invoiced *(1-(line.order_id.ks_global_discount_rate/100))

    # @api.depends('state', 'price_reduce', 'product_id', 'untaxed_amount_invoiced', 'qty_delivered', 'product_uom_qty','untaxed_amount_to_invoice')
    # def _compute_yds_untaxed_amount_to_invoice(self):
    #     print("~~~~~~~~~~~~~~~~~~~~~`````editing untaxted_amount_to_invoice~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
    #     for line in self:
    #         if line.untaxed_amount_to_invoice != 0:
    #             line.yds_untaxed_amount_to_invoice = line.untaxed_amount_to_invoice*(1-(line.order_id.ks_global_discount_rate/100))

    @api.depends('invoice_lines', 'invoice_lines.price_total', 'invoice_lines.move_id.state', 'invoice_lines.move_id.move_type')
    def _compute_untaxed_amount_invoiced(self):
        """ Compute the untaxed amount already invoiced from the sale order line, taking the refund attached
            the so line into account. This amount is computed as
                SUM(inv_line.price_subtotal) - SUM(ref_line.price_subtotal)
            where
                `inv_line` is a customer invoice line linked to the SO line
                `ref_line` is a customer credit note (refund) line linked to the SO line
        """
        for line in self:
            amount_invoiced = 0.0
            for invoice_line in line.invoice_lines:
                if invoice_line.move_id.state == 'posted':
                    invoice_date = invoice_line.move_id.invoice_date or fields.Date.today()
                    if invoice_line.move_id.move_type == 'out_invoice':
                        amount_invoiced += invoice_line.currency_id._convert(invoice_line.price_subtotal*(1-invoice_line.discount/100)*(1-(invoice_line.move_id.ks_global_discount_rate) / 100), line.currency_id, line.company_id, invoice_date)
                    elif invoice_line.move_id.move_type == 'out_refund':
                        amount_invoiced -= invoice_line.currency_id._convert(invoice_line.price_subtotal*(1-invoice_line.discount/100)*(1-(invoice_line.move_id.ks_global_discount_rate) / 100), line.currency_id, line.company_id, invoice_date)
                        
            line.untaxed_amount_invoiced = amount_invoiced
    
    @api.depends('state', 'price_reduce', 'product_id', 'untaxed_amount_invoiced', 'qty_delivered', 'product_uom_qty')
    def _compute_untaxed_amount_to_invoice(self):
        """ Total of remaining amount to invoice on the sale order line (taxes excl.) as
                total_sol - amount already invoiced
            where Total_sol depends on the invoice policy of the product.

            Note: Draft invoice are ignored on purpose, the 'to invoice' amount should
            come only from the SO lines.
        """
        for line in self:
            amount_to_invoice = 0.0
            if line.state in ['sale', 'done']:
                # Note: do not use price_subtotal field as it returns zero when the ordered quantity is
                # zero. It causes problem for expense line (e.i.: ordered qty = 0, deli qty = 4,
                # price_unit = 20 ; subtotal is zero), but when you can invoice the line, you see an
                # amount and not zero. Since we compute untaxed amount, we can use directly the price
                # reduce (to include discount) without using `compute_all()` method on taxes.
                price_subtotal = 0.0
                if line.product_id.invoice_policy == 'delivery':
                    price_subtotal = line.price_reduce * line.qty_delivered
                else:
                    price_subtotal = line.price_reduce * line.product_uom_qty
                if len(line.tax_id.filtered(lambda tax: tax.price_include)) > 0:
                    # As included taxes are not excluded from the computed subtotal, `compute_all()` method
                    # has to be called to retrieve the subtotal without them.
                    # `price_reduce_taxexcl` cannot be used as it is computed from `price_subtotal` field. (see upper Note)
                    price_subtotal = line.tax_id.compute_all(
                        price_subtotal,
                        currency=line.order_id.currency_id,
                        quantity=line.product_uom_qty,
                        product=line.product_id,
                        partner=line.order_id.partner_shipping_id)['total_excluded']

                if any(line.invoice_lines.mapped(lambda l: l.discount != line.discount)):
                    # In case of re-invoicing with different discount we try to calculate manually the
                    # remaining amount to invoice
                    amount = 0
                    for l in line.invoice_lines:
                        if len(l.tax_ids.filtered(lambda tax: tax.price_include)) > 0:
                            amount += l.tax_ids.compute_all(l.currency_id._convert(l.price_unit, line.currency_id, line.company_id, l.date or fields.Date.today(), round=False) * l.quantity)['total_excluded'] 
                        else:
                            amount += l.currency_id._convert(l.price_unit, line.currency_id, line.company_id, l.date or fields.Date.today(), round=False) * l.quantity

                    amount_to_invoice = max(price_subtotal*(1-line.order_id.ks_global_discount_rate/100)  - amount, 0)
                else:
                    amount_to_invoice = price_subtotal*(1-line.order_id.ks_global_discount_rate/100)  - line.untaxed_amount_invoiced 
            line.untaxed_amount_to_invoice = amount_to_invoice


    @api.depends('product_uom_qty', 'discount', 'price_unit', 'tax_id', 'yds_global_discount_rate')
    def _compute_amount(self):
        """
        Compute the amounts of the SO line.
        """
        for line in self:
            price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)

            # original price
            x_price = line.price_unit
            x_price_w_uni = line.price_unit * \
                (1 - (line.discount or 0.0) / 100.0) * \
                (1 - (line.order_id.ks_global_discount_rate / 100))

            # Use price_unit instead of Odoo's DEFAULT line_discount_price_unit to calc tax without discount
            # To seperate discount from net sales
            taxes = line.tax_id.compute_all(price, line.order_id.currency_id, line.product_uom_qty,
                                            product=line.product_id, partner=line.order_id.partner_shipping_id)
            x_taxes = line.tax_id.compute_all(x_price, line.order_id.currency_id, line.product_uom_qty,
                                              product=line.product_id, partner=line.order_id.partner_shipping_id)
            x_taxes_uni = line.tax_id.compute_all(
                x_price_w_uni, line.order_id.currency_id, line.product_uom_qty, product=line.product_id, partner=line.order_id.partner_shipping_id)
            line.update({
                'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                # price with normal discount
                'price_total': taxes['total_included'],
                'price_subtotal': taxes['total_excluded'],

                # price without any discount
                'x_price_subtotal_wo_uni': x_taxes['total_excluded'],
                'x_price_total_wo_uni': x_taxes['total_included'],

                # price with all discounts
                'x_price_subtotal': x_taxes_uni['total_excluded'],
                'x_price_total': x_taxes_uni['total_included'],
            })
            if self.env.context.get('import_file', False) and not self.env.user.user_has_groups('account.group_account_manager'):
                line.tax_id.invalidate_cache(
                    ['invoice_repartition_line_ids'], [line.tax_id.id])

    # Ensure no lines have the same label to avoid discount lines not being created
        # def write(self, vals):
        #     print("Sale WRITE CALLED")
        #     for line in self.order_id.order_line:
        #         for l in self.order_id.order_line - line:
        #             if line.name and line.name == l.name:
        #                 raise UserError(_("One or more line have the same Label."))
        #     return super(SaleOrderlineTemplate, self).write(vals)

    # Change how Odoo sets the default label of lines

    @api.onchange('product_id')
    def rename_description(self):
        if not self.product_id:
            return
        self.name = self.product_id.name
        if self.product_id.description_sale:
            self.name = self.product_id.name + " - " + self.product_id.description_sale


class PurchaseOrderlineTemplate(models.Model):
    _inherit = 'purchase.order.line'
 # Change how Odoo sets the default label of lines

    @api.onchange('product_id')
    def rename_description(self):
        if not self.product_id:
            return
        self.name = self.product_id.name
        if self.product_id.description_purchase:
            self.name = self.product_id.description_purchase
