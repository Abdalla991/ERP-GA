from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError


class Company(models.Model):
    _inherit = "res.company"
    yds_enable_discount_account = fields.Boolean(string="Activate Pricelist Discount Account")


class YDSResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    yds_enable_discount_account = fields.Boolean(string="Activate Pricelist Discount Account", related='company_id.yds_enable_discount_account', readonly=False)
 
class YDSPricelist(models.Model):
    _inherit = "product.pricelist"
    yds_assigned_discount_account = fields.Many2one('account.account', string="Pricelist Discount Account", readonly=False)
    yds_enable_discount_account = fields.Boolean(compute='yds_verify_enable')
    
    
    
    @api.depends('company_id.yds_enable_discount_account')
    def yds_verify_enable(self):
        for rec in self:
            rec.yds_enable_discount_account = rec.company_id.yds_enable_discount_account

class YDSSaleOrder(models.Model):
    _inherit = "sale.order"

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




class YDSAccountMoveLine(models.Model):
    _inherit = "account.move.line"
    yds_price_subtotal = fields.Monetary(string='Subtotal', store=True, readonly=True, currency_field='currency_id')
    yds_price_total = fields.Monetary(string='Total', store=True, readonly=True,currency_field='currency_id')
    @api.model
    def _get_price_total_and_subtotal_model(self, price_unit, quantity, discount, currency, product, partner, taxes, move_type):
        res = {}

        # Compute 'price_subtotal'.
        line_discount_price_unit = price_unit * (1 - (discount / 100.0))
        subtotal = quantity * line_discount_price_unit
        
        yds_subtotal = quantity * price_unit

        # Compute 'price_total'.
        if taxes:
            taxes_res = taxes._origin.compute_all(line_discount_price_unit,
                quantity=quantity, currency=currency, product=product, partner=partner, is_refund=move_type in ('out_refund', 'in_refund'))
            res['price_subtotal'] = taxes_res['total_excluded'] /(1 - (discount / 100.0)) 
            res['price_total'] = taxes_res['total_included']
            #change res['debit']
            res['yds_price_subtotal'] = taxes_res['total_excluded'] /(1 - (discount / 100.0)) 
            res['yds_price_total'] = taxes_res['total_included'] /(1 - (discount / 100.0))
        else:
            res['price_total'] = res['price_subtotal'] = subtotal
            res['yds_price_total'] = res['yds_price_subtotal'] = yds_subtotal
        #In case of multi currency, round before it's use for computing debit credit
        if currency:
            res = {k: currency.round(v) for k, v in res.items()}
        return res
    
    def _prepare_analytic_line(self):
        """ Prepare the values used to create() an account.analytic.line upon validation of an account.move.line having
            an analytic account. This method is intended to be extended in other modules.
            :return list of values to create analytic.line
            :rtype list
        """
        for move_line in self:
            amount = (move_line.credit or 0.0) - (move_line.debit or 0.0)
            params = {
                "amount":[amount,(move_line.price_unit * ( (move_line.discount or 0.0) / 100.0) * move_line.quantity)*-1,move_line.move_id.ks_amount_discount*-1],
                "name":["amount","discount","Universal discount"] 
                }
                #TEST PER PRODUCT
                #FIX ACCOUNT IDS
        result = []
        for  i in range(3):  #3 because we want 3 entries (amount,discount,global discount)
            for move_line in self:
                amount = (move_line.credit or 0.0) - (move_line.debit or 0.0)
                default_name = move_line.name or (move_line.ref or '/' + ' -- ' + (move_line.partner_id and move_line.partner_id.name or '/'))
                result.append({
                    'name': default_name +" "+params["name"][i],
                    'date': move_line.date,
                    'account_id': move_line.analytic_account_id.id,
                    'group_id': move_line.analytic_account_id.group_id.id,
                    'tag_ids': [(6, 0, move_line._get_analytic_tag_ids())],
                    'unit_amount': move_line.quantity,
                    'product_id': move_line.product_id and move_line.product_id.id or False,
                    'product_uom_id': move_line.product_uom_id and move_line.product_uom_id.id or False,
                    'amount': params["amount"][i],
                    'general_account_id': move_line.account_id.id,
                    'ref': move_line.ref,
                    'move_id': move_line.id,
                    'user_id': move_line.move_id.invoice_user_id.id or self._uid,
                    'partner_id': move_line.partner_id.id,
                    'company_id': move_line.analytic_account_id.company_id.id or self.env.company.id,
                    'yds_product_discount': move_line.price_unit * ( (move_line.discount or 0.0) / 100.0) * move_line.quantity,
                })
        return result

class YDSAccountMove(models.Model):
    _inherit = "account.move"
    yds_total_discount = fields.Float(string='Total Discount',readonly=True,store=True)
    yds_pricelist_account_id = fields.Integer(string='Pricelist account ID',  readonly=True,store=True)
    yds_pricelist_name = fields.Char(string ='Pricelist Name',readonly=True,store=True)

    yds_amount_untaxed = fields.Monetary(string='Untaxed Amount', store=True, readonly=True, currency_field='company_currency_id')
    yds_amount_untaxed_after_discount = fields.Monetary(string='Untaxed Amount After Discount', store=True, readonly=True, currency_field='company_currency_id')
    yds_is_sales_order = fields.Boolean(string="is Sales Order")

    #added because of the change in pricelist subtotal
    yds_amount_total = fields.Monetary(string='Total', store=True, readonly=True, compute='_compute_amount2')

    @api.depends(
        'line_ids.debit',
        'line_ids.credit',
        'line_ids.currency_id',
        'line_ids.amount_currency',
        'line_ids.amount_residual',
        'line_ids.amount_residual_currency',
        'line_ids.payment_id.state',
        'line_ids.price_subtotal',   #change to moataz's new variable
        'yds_total_discount')
    def _compute_amount(self):
        super(YDSAccountMove, self)._compute_amount()
        for rec in self:
            
            rec.yds_total_discount=0
            rec._calculatePricelistDiscount()
            rec.amount_total = rec.amount_tax + rec.amount_untaxed - rec.yds_total_discount
            rec.update_pricelist_account()
            #depending on the change of the price_subtotal field
            rec.yds_amount_untaxed = rec.amount_untaxed
            rec.yds_amount_untaxed_after_discount = rec.yds_amount_untaxed - rec.yds_total_discount
    
    @api.depends('amount_total')
    def _compute_amount2(self):
        for rec in self:
            rec.yds_amount_total = rec.amount_total - rec.yds_total_discount


    def _calculatePricelistDiscount(self):
        for rec in self:
         for line in rec.line_ids:
                rec.yds_total_discount += line.price_unit * ( (line.discount or 0.0) / 100.0) * line.quantity
    
    def update_pricelist_account(self):
        """This Function Updates the Universal Discount through Sale Order"""
        for rec in self:
            already_exists = self.line_ids.filtered(
                lambda line: line.name and line.name.find('Pricelist Discount') == 0)
            terms_lines = self.line_ids.filtered(
                lambda line: line.account_id.user_type_id.type in ('receivable', 'payable'))
            other_lines = self.line_ids.filtered(
                lambda line: line.account_id.user_type_id.type not in ('receivable', 'payable'))
            if already_exists:
                amount = rec.yds_total_discount
                if rec.yds_pricelist_account_id \
                        and (rec.move_type == "out_invoice"
                             or rec.move_type == "out_refund")\
                        and amount > 0:
                    if rec.move_type == "out_invoice":
                        already_exists.update({
                            'debit': amount > 0.0 and amount or 0.0,
                            'credit': amount < 0.0 and -amount or 0.0,
                        })
                    else:
                        already_exists.update({
                            'debit': amount < 0.0 and -amount or 0.0,
                            'credit': amount > 0.0 and amount or 0.0,
                        })
                total_balance = sum(other_lines.mapped('balance'))
                total_amount_currency = sum(other_lines.mapped('amount_currency'))
                terms_lines.update({
                    'amount_currency': -total_amount_currency,
                    'debit': total_balance < 0.0 and -total_balance or 0.0,
                    'credit': total_balance > 0.0 and total_balance or 0.0,
                })
            if not already_exists and rec.yds_total_discount > 0:
                in_draft_mode = self != self._origin
                if not in_draft_mode and rec.move_type == 'out_invoice':
                    rec._add_pricelist_account_lines()
                print()


    @api.onchange('yds_total_discount','line_ids')
    def _add_pricelist_account_lines(self): #when is this called ?
        """This Function Create The General Entries for Pricelist Discount"""
        for rec in self:
            type_list = ['out_invoice', 'out_refund', 'in_invoice', 'in_refund']
            if rec.yds_total_discount > 0 and rec.move_type in type_list:
                if rec.is_invoice(include_receipts=True):
                    in_draft_mode = self != self._origin
                    yds_name = "Pricelist Discount " + str(rec.yds_pricelist_name)
                    #           ("Invoice No: " + str(self.ids)
                    #            if self._origin.id
                    #            else (self.display_name))
                    terms_lines = self.line_ids.filtered(
                        lambda line: line.account_id.user_type_id.type in ('receivable', 'payable'))
                    already_exists = self.line_ids.filtered(
                                    lambda line: line.name and line.name.find('Pricelist Discount') == 0)
                    if already_exists:
                        amount = self.yds_total_discount
                        if self.yds_pricelist_account_id \
                                and (self.move_type == "out_invoice"
                                     or self.move_type == "out_refund"):
                            if self.move_type == "out_invoice":
                                already_exists.update({
                                    'name': yds_name,
                                    'debit': amount > 0.0 and amount or 0.0,
                                    'credit': amount < 0.0 and -amount or 0.0,
                                })
                            else:
                                already_exists.update({
                                    'name': yds_name,
                                    'debit': amount < 0.0 and -amount or 0.0,
                                    'credit': amount > 0.0 and amount or 0.0,
                                })
                    else:
                        new_tax_line = self.env['account.move.line']
                        create_method = in_draft_mode and \
                                        self.env['account.move.line'].new or\
                                        self.env['account.move.line'].create

                        if self.yds_pricelist_account_id \
                                and (self.move_type == "out_invoice"
                                     or self.move_type == "out_refund"):
                            amount = self.yds_total_discount
                            dict = {
                                    'move_name': self.name,
                                    'name': yds_name,
                                    'price_unit': self.yds_total_discount,
                                    'quantity': 1,
                                    'debit': amount < 0.0 and -amount or 0.0,
                                    'credit': amount > 0.0 and amount or 0.0,
                                    'account_id': self.yds_pricelist_account_id,
                                    'move_id': self._origin,
                                    'date': self.date,
                                    'exclude_from_invoice_tab': True,
                                    'partner_id': terms_lines.partner_id.id,
                                    'company_id': terms_lines.company_id.id,
                                    'company_currency_id': terms_lines.company_currency_id.id,
                                    }
                            if self.move_type == "out_invoice":
                                dict.update({
                                    'debit': amount > 0.0 and amount or 0.0,
                                    'credit': amount < 0.0 and -amount or 0.0,
                                })
                            else:
                                dict.update({
                                    'debit': amount < 0.0 and -amount or 0.0,
                                    'credit': amount > 0.0 and amount or 0.0,
                                })
                            if in_draft_mode:
                                self.line_ids += create_method(dict)
                                # Updation of Invoice Line Id
                                duplicate_id = self.invoice_line_ids.filtered(
                                    lambda line: line.name and line.name.find('Pricelist Discount') == 0)
                                self.invoice_line_ids = self.invoice_line_ids - duplicate_id
                            else:
                                dict.update({
                                    'price_unit': 0.0,
                                    'debit': 0.0,
                                    'credit': 0.0,
                                })
                                self.line_ids = [(0, 0, dict)]
                    if in_draft_mode:
                        # Update the payement account amount
                        terms_lines = self.line_ids.filtered(
                            lambda line: line.account_id.user_type_id.type in ('receivable', 'payable'))
                        other_lines = self.line_ids.filtered(
                            lambda line: line.account_id.user_type_id.type not in ('receivable', 'payable'))
                        total_balance = sum(other_lines.mapped('balance'))  
                        total_amount_currency = sum(other_lines.mapped('amount_currency'))
                        terms_lines.update({
                                    'amount_currency': -total_amount_currency,
                                    'debit': total_balance < 0.0 and -total_balance or 0.0,
                                    'credit': total_balance > 0.0 and total_balance or 0.0,
                                })
                    else:
                        amount = self.yds_total_discount
                        terms_lines = self.line_ids.filtered(
                            lambda line: line.account_id.user_type_id.type in ('receivable', 'payable'))
                        other_lines = self.line_ids.filtered(
                            lambda line: line.account_id.user_type_id.type not in ('receivable', 'payable'))
                        already_exists = self.line_ids.filtered(
                            lambda line: line.name and line.name.find('Pricelist Discount') == 0)
                        total_balance = sum(other_lines.mapped('balance')) + amount
                        total_amount_currency = sum(other_lines.mapped('amount_currency'))
                        dict1 = {
                                    'debit': amount > 0.0 and amount or 0.0,
                                    'credit': amount < 0.0 and -amount or 0.0,
                        }
                        dict2 = {
                                'debit': total_balance < 0.0 and -total_balance or 0.0,
                                'credit': total_balance > 0.0 and total_balance or 0.0,
                                }
                        self.line_ids = [(1, already_exists.id, dict1), (1, terms_lines.id, dict2)]
                        print()

            elif self.yds_total_discount <= 0:
                already_exists = self.line_ids.filtered(
                    lambda line: line.name and line.name.find('Pricelist Discount') == 0)
                if already_exists:
                    self.line_ids -= already_exists
                    terms_lines = self.line_ids.filtered(
                        lambda line: line.account_id.user_type_id.type in ('receivable', 'payable'))
                    other_lines = self.line_ids.filtered(
                        lambda line: line.account_id.user_type_id.type not in ('receivable', 'payable'))
                    total_balance = sum(other_lines.mapped('balance'))
                    total_amount_currency = sum(other_lines.mapped('amount_currency'))
                    terms_lines.update({
                        'amount_currency': -total_amount_currency,
                        'debit': total_balance < 0.0 and -total_balance or 0.0,
                        'credit': total_balance > 0.0 and total_balance or 0.0,
                    })



class YDSAccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'
    yds_product_discount = fields.Float(string='Total Product Discounts', store=True, readonly=True)
