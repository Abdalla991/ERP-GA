from odoo import models, fields, api, exceptions, _
from odoo.exceptions import UserError, ValidationError


class YDSAccountMovePricelist(models.Model):
    _inherit = "account.move"


    pricelist_id = fields.Many2one(
        'product.pricelist', string='Pricelist', check_company=True,  # Unrequired company
        required=True, readonly=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]},
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]", tracking=1,
        help="If you change the pricelist, only newly added lines will be affected.")

    show_update_pricelist = fields.Boolean(string='Has Pricelist Changed',
                                           help="Technical Field, True if the pricelist was changed;\n"
                                                " this will then display a recomputation button")

                                
                             
    @api.onchange('pricelist_id')
    def _onchange_pricelist_id(self):
        if self.invoice_line_ids and self.pricelist_id and self._origin.pricelist_id and self._origin.pricelist_id != self.pricelist_id:
            self.show_update_pricelist = True
        else:
            self.show_update_pricelist = False

    def update_prices(self):
        
        # (lambda line: not line.display_type)
        self.ensure_one()
        lines_to_update = []
        for line in self.invoice_line_ids.filtered(lambda line: not line.display_type):
            product = line.product_id.with_context(
                partner=self.partner_id,
                quantity=line.quantity,
                date=self.date,
                pricelist=self.pricelist_id.id,
                uom=line.product_uom_id.id
            )
            print("update_prices called")
            price_unit = self.env['account.tax']._fix_tax_included_price_company(
                line._get_display_price(product), line.product_id.taxes_id, line.tax_line_id, line.company_id)
            if self.pricelist_id.discount_policy == 'without_discount':
                discount = max(0, (price_unit - product.price) * 100 / price_unit)
            else:
                discount = 0
            lines_to_update.append((1, line.id, {'price_unit': price_unit, 'discount': discount}))
        self.update({'invoice_line_ids': lines_to_update})
        self.show_update_pricelist = False
        self.message_post(body=_("Product prices have been recomputed according to pricelist <b>%s<b> ", self.pricelist_id.display_name))

 
 
class YDSAccountMoveLinePricelist(models.Model):
    _inherit = "account.move.line"



    @api.onchange('product_uom_id', 'quantity')
    def product_uom_change(self):
        if not self.product_uom_id or not self.product_id:
            self.price_unit = 0.0
            return
        if self.move_id.pricelist_id and self.move_id.partner_id:
            product = self.product_id.with_context(
                lang=self.move_id.partner_id.lang,
                partner=self.move_id.partner_id,
                quantity=self.quantity,
                date=self.move_id.date,
                pricelist=self.move_id.pricelist_id.id,
                uom=self.product_uom_id.id,
                fiscal_position=self.env.context.get('fiscal_position')
            )
            self.price_unit = self.env['account.tax']._fix_tax_included_price_company(self._get_display_price(product), product.taxes_id, self.tax_line_id, self.company_id)


    def _get_display_price(self, product):
        print("_get_display_price called")
        if self.move_id.pricelist_id.discount_policy == 'with_discount':
            return product.with_context(pricelist=self.move_id.pricelist_id.id).price
        product_context = dict(self.env.context, partner_id=self.move_id.partner_id.id, date=self.move_id.date, uom=self.product_uom_id.id)

        final_price, rule_id = self.move_id.pricelist_id.with_context(product_context).get_product_price_rule(product or self.product_id, self.quantity or 1.0, self.move_id.partner_id)
        base_price, currency = self.with_context(product_context)._get_real_price_currency(product, rule_id, self.quantity, self.product_uom_id, self.move_id.pricelist_id.id)
        if currency != self.move_id.pricelist_id.currency_id:
            base_price = currency._convert(
                base_price, self.move_id.pricelist_id.currency_id,
                self.move_id.company_id or self.env.company, self.move_id.date or fields.Date.today())
        # negative discounts (= surcharge) are included in the display price
        return max(base_price, final_price)

    def _get_real_price_currency(self, product, rule_id, qty, uom, pricelist_id):
        """Retrieve the price before applying the pricelist
            :param obj product: object of current product record
            :parem float qty: total quentity of product
            :param tuple price_and_rule: tuple(price, suitable_rule) coming from pricelist computation
            :param obj uom: unit of measure of current order line
            :param integer pricelist_id: pricelist id of sales order"""
        PricelistItem = self.env['product.pricelist.item']
        field_name = 'lst_price'
        currency_id = None
        product_currency = product.currency_id
        if rule_id:
            pricelist_item = PricelistItem.browse(rule_id)
            if pricelist_item.pricelist_id.discount_policy == 'without_discount':
                while pricelist_item.base == 'pricelist' and pricelist_item.base_pricelist_id and pricelist_item.base_pricelist_id.discount_policy == 'without_discount':
                    price, rule_id = pricelist_item.base_pricelist_id.with_context(uom=uom.id).get_product_price_rule(product, qty, self.move_id.partner_id)
                    pricelist_item = PricelistItem.browse(rule_id)

            if pricelist_item.base == 'standard_price':
                field_name = 'standard_price'
                product_currency = product.cost_currency_id
            elif pricelist_item.base == 'pricelist' and pricelist_item.base_pricelist_id:
                field_name = 'price'
                product = product.with_context(pricelist=pricelist_item.base_pricelist_id.id)
                product_currency = pricelist_item.base_pricelist_id.currency_id
            currency_id = pricelist_item.pricelist_id.currency_id

        if not currency_id:
            currency_id = product_currency
            cur_factor = 1.0
        else:
            if currency_id.id == product_currency.id:
                cur_factor = 1.0
            else:
                cur_factor = currency_id._get_conversion_rate(product_currency, currency_id, self.company_id or self.env.company, self.move_id.date or fields.Date.today())

        product_uom = self.env.context.get('uom') or product.uom_id.id
        print()
        if uom and uom.id != product_uom:
            # the unit price is in a different uom
            uom_factor = uom._compute_price(1.0, product.uom_id)
        else:
            uom_factor = 1.0

        return product[field_name] * uom_factor * cur_factor, currency_id


    @api.onchange('product_id', 'price_unit', 'product_uom_id', 'quantity', 'tax_line_id')
    def _onchange_discount(self):
        if not (self.product_id and self.product_uom_id and
                self.move_id.partner_id and self.move_id.pricelist_id and
                self.move_id.pricelist_id.discount_policy == 'without_discount' and
                self.env.user.has_group('product.group_discount_per_so_line')):
            return

        self.discount = 0.0
        product = self.product_id.with_context(
            lang=self.move_id.partner_id.lang,
            partner=self.move_id.partner_id,
            quantity=self.quantity,
            date=self.move_id.date,
            pricelist=self.move_id.pricelist_id.id,
            uom=self.product_uom_id.id,
            fiscal_position=self.env.context.get('fiscal_position')
        )

        product_context = dict(self.env.context, partner_id=self.move_id.partner_id.id, date=self.move_id.date, uom=self.product_uom_id.id)

        price, rule_id = self.move_id.pricelist_id.with_context(product_context).get_product_price_rule(self.product_id, self.quantity or 1.0, self.move_id.partner_id)
        new_list_price, currency = self.with_context(product_context)._get_real_price_currency(product, rule_id, self.quantity, self.product_uom_id, self.move_id.pricelist_id.id)

        if new_list_price != 0:
            if self.move_id.pricelist_id.currency_id != currency:
                # we need new_list_price in the same currency as price, which is in the SO's pricelist's currency
                new_list_price = currency._convert(
                    new_list_price, self.move_id.pricelist_id.currency_id,
                    self.move_id.company_id or self.env.company, self.move_id.date or fields.Date.today())
            discount = (new_list_price - price) / new_list_price * 100
            if (discount > 0 and new_list_price > 0) or (discount < 0 and new_list_price < 0):
                self.discount = discount


# incase of a sale order -> send pricelist_id to account.move           
class YDSSaleOrderPricelist(models.Model):
    _inherit = "sale.order"

    def _prepare_invoice(self):
        res = super(YDSSaleOrderPricelist, self)._prepare_invoice()
        res['pricelist_id'] = self.pricelist_id

            
        return res