from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools.misc import formatLang
import ipdb


class KsGlobalDiscountInvoice(models.Model):
    # _inherit = "account.invoice"
    """ changing the model to account.move """
    _inherit = "account.move"


    ks_global_discount_type = fields.Selection([('percent', 'Percentage')],
                                               string='Universal Discount Type', readonly=True,
                                               default='percent')
    ks_global_discount_rate = fields.Float('Universal Discount',
                                           readonly=True,
                                           states={'draft': [('readonly', False)],
                                                   'sent': [('readonly', False)]}
                                                   )
    ks_amount_discount = fields.Monetary(string='Universal Discount',
                                         readonly=True,
                                         compute='_compute_amount',
                                         store=True, track_visibility='always')
    ks_enable_discount = fields.Boolean(compute='ks_verify_discount')
    ks_sales_discount_account_id = fields.Integer(compute='ks_verify_discount')
    ks_purchase_discount_account_id = fields.Integer(compute='ks_verify_discount')

    yds_amount_tax = fields.Monetary(string='Tax', store=True, readonly=True)

    @api.depends('company_id.ks_enable_discount')
    def ks_verify_discount(self):
        for rec in self:
            rec.ks_enable_discount = rec.company_id.ks_enable_discount
            rec.ks_sales_discount_account_id = rec.company_id.ks_sales_discount_account.id
            rec.ks_purchase_discount_account_id = rec.company_id.ks_purchase_discount_account.id

    @api.onchange('partner_id')
    def calc_uni_rate(self):
        for rec in self:
            rec.ks_global_discount_rate = rec.partner_id.yds_customer_universal_discount_rate
    # 1. tax_line_ids is replaced with tax_line_id. 2. api.mulit is also removed.
    @api.depends(
        'line_ids.debit',
        'line_ids.credit',
        'line_ids.currency_id',
        'line_ids.amount_currency',
        'line_ids.amount_residual',
        'line_ids.amount_residual_currency',
        'line_ids.payment_id.state',
        'ks_global_discount_type',
        'ks_global_discount_rate')
    def _compute_amount(self):
        super(KsGlobalDiscountInvoice, self)._compute_amount()
        for rec in self:
            if not ('ks_global_tax_rate' in rec):
                rec.ks_calculate_discount()
            sign = rec.move_type in ['in_refund', 'out_refund'] and -1 or 1
            rec.amount_total_signed = rec.amount_total * sign
            # rec.amount_tax = sign * (total_tax_currency if len(currencies) == 1 else total_tax) * (1-rec.ks_global_discount_rate/100)
            # rec.amount_untaxed_signed = -total_untaxed * (1-rec.ks_global_discount_rate/100)







    # @api.multi
    def ks_calculate_discount(self):
        for rec in self:
            difference = 0
            if rec.ks_global_discount_type == "amount":
                rec.ks_amount_discount = rec.ks_global_discount_rate if rec.yds_amount_untaxed_after_discount > 0 else 0
            elif rec.ks_global_discount_type == "percent":
                if rec.ks_global_discount_rate != 0.0:
                    rec.ks_amount_discount = (rec.yds_amount_untaxed_after_discount) * rec.ks_global_discount_rate / 100
                else:
                    rec.ks_amount_discount = 0
            elif not rec.ks_global_discount_type:
                rec.ks_global_discount_rate = 0
                rec.ks_amount_discount = 0
            
            if rec.payment_state == 'invoicing_legacy':
                # invoicing_legacy state is set via SQL when setting setting field
                # invoicing_switch_threshold (defined in account_accountant).
                # The only way of going out of this state is through this setting,
                # so we don't recompute it here.
                rec.payment_state = rec.payment_state
                continue

            total_untaxed = 0.0
            total_untaxed_currency = 0.0
            total_tax = 0.0
            total_tax_currency = 0.0
            total_to_pay = 0.0
            total_residual = 0.0
            total_residual_currency = 0.0
            total = 0.0
            total_currency = 0.0
            currencies = set()

            for line in rec.line_ids:
                if line.currency_id:
                    currencies.add(line.currency_id)

                if rec.is_invoice(include_receipts=True):
                    # === Invoices ===

                    if not line.exclude_from_invoice_tab:
                        # Untaxed amount.
                        total_untaxed += line.balance
                        total_untaxed_currency += line.amount_currency
                        total += line.balance
                        total_currency += line.amount_currency
                    elif line.tax_line_id:
                        # Tax amount.
                        total_tax += line.balance
                        total_tax_currency += line.amount_currency
                        total += line.balance
                        total_currency += line.amount_currency
                    elif line.account_id.user_type_id.type in ('receivable', 'payable'):
                        # Residual amount.
                        total_to_pay += line.balance
                        total_residual += line.amount_residual
                        total_residual_currency += line.amount_residual_currency
                else:
                    # === Miscellaneous journal entry ===
                    if line.debit:
                        total += line.balance
                        total_currency += line.amount_currency

            if rec.move_type == 'entry' or rec.is_outbound():
                sign = 1
            else:
                sign = -1

            # rec.ks_amount_discount = rec.ks_amount_discount - rec.yds_total_discount
            rec.amount_total = rec.amount_tax + rec.amount_untaxed - rec.ks_amount_discount
            # rec.amount_untaxed -= rec.ks_amount_discount
            rec.yds_amount_tax = rec.amount_tax

            rec.amount_tax = rec.amount_tax * (1-rec.ks_global_discount_rate/100)
            rec.amount_tax_signed = rec.amount_tax_signed * (1-rec.ks_global_discount_rate/100)
            difference = rec.yds_amount_tax - rec.amount_tax
            rec.amount_residual = -sign * (total_residual_currency if len(currencies) == 1 else total_residual) - difference
            rec.yds_amount_total = rec.amount_tax + rec.yds_amount_untaxed_after_discount - rec.ks_amount_discount
            # rec.yds_amount_untaxed_after_discount -= rec.ks_amount_discount
            rec.add_lines_uni()


    
    
    
    @api.constrains('ks_global_discount_rate')
    def ks_check_discount_value(self):
        if self.ks_global_discount_type == "percent":
            if self.ks_global_discount_rate > 100 or self.ks_global_discount_rate < 0:
                raise ValidationError('You cannot enter percentage value greater than 100.')
        else:
            if self.ks_global_discount_rate < 0 or self.amount_untaxed < 0:
                raise ValidationError(
                    'You cannot enter discount amount greater than actual cost or value lower than 0.')

    @api.model
    def _prepare_refund(self, invoice, date_invoice=None, date=None, description=None, journal_id=None):
        ks_res = super(KsGlobalDiscountInvoice, self)._prepare_refund(invoice, date_invoice=None, date=None,
                                                                      description=None, journal_id=None)
        ks_res['ks_global_discount_rate'] = self.ks_global_discount_rate
        ks_res['ks_global_discount_type'] = self.ks_global_discount_type
        return ks_res
    


    def add_lines_uni(self):       
        # OVERRIDE
        # Don't change anything on moves used to cancel another ones.
        # return super()._post(soft=False)
        print("add_lines for universal called")
        type_list = ['out_invoice', 'out_refund', 'in_invoice', 'in_refund']

        for move in self:
            count =0  #for counting loops
            if move.is_invoice(include_receipts=True):
                for line in move.invoice_line_ids:
                    count+=1
                    print(count)
                    exists = False
                    # Filter out lines being not eligible for discount/universal discount line.
                    if line.product_id.type != 'product' or line.product_id.valuation != 'real_time':
                        continue

                    sale_uni_discount_account = move.ks_sales_discount_account_id
                    purchase_uni_discount_account = move.ks_purchase_discount_account_id
                    # unversal_discount_account = accounts['expense'] or self.journal_id.default_account_id
                    if not sale_uni_discount_account or not purchase_uni_discount_account:
                        continue

                    sign = -1 if move.move_type == 'out_refund' else 1
                    # price_unit = line.price_unit
                    # balance = sign * line.quantity * price_unit

                    #Calculations
                    uni_discount_rate=move.ks_global_discount_rate/100
                    amount = ((line.credit or 0.0) - (line.debit or 0.0))*sign
                    pricelist_discount_line_amount =(line.price_unit * ( (line.discount or 0.0) / 100.0) *line.quantity)
                    hasDiscount = uni_discount_rate > 0

                    if(hasDiscount):
                        universal_discount_line_amount = ((amount-pricelist_discount_line_amount)*uni_discount_rate)
                        print("line "+str(count)+"has "+"uni discount of " +str(universal_discount_line_amount))
                    else:
                        universal_discount_line_amount=0

                    
                    lineName =  line.name[:64]+" Universal discount "
                    already_exists = self.line_ids.filtered(
                        lambda line: line.name and line.name.find(lineName) == 0)
                    terms_lines = self.line_ids.filtered(
                        lambda line: line.account_id.user_type_id.type in ('receivable', 'payable'))
                    other_lines = self.line_ids.filtered(
                        lambda line: line.account_id.user_type_id.type not in ('receivable', 'payable'))
                    if already_exists:
                        print("Uni Aleady exisits 1 "+line.name)
                        exists=True
                        amount = universal_discount_line_amount
                        if sale_uni_discount_account \
                                and (move.move_type == "out_invoice"
                                    or move.move_type == "out_refund")\
                                and amount > 0:
                            if move.move_type == "out_invoice":
                                already_exists.update({
                                    'debit': amount > 0.0 and amount or 0.0,
                                    'credit': amount < 0.0 and -amount or 0.0,
                                })
                            else:
                                already_exists.update({
                                    'debit': amount < 0.0 and -amount or 0.0,
                                    'credit': amount > 0.0 and amount or 0.0,
                                })
                        if purchase_uni_discount_account \
                                and (move.move_type == "in_invoice"
                                        or move.move_type == "in_refund")\
                                and amount > 0:
                            if move.move_type == "in_invoice":
                                already_exists.update({
                                    'debit': amount < 0.0 and -amount or 0.0,
                                    'credit': amount > 0.0 and amount or 0.0,
                                })
                            else:
                                already_exists.update({
                                    'debit': amount > 0.0 and amount or 0.0,
                                    'credit': amount < 0.0 and -amount or 0.0,
                                })
                        total_balance = sum(other_lines.mapped('balance'))
                        total_amount_currency = sum(other_lines.mapped('amount_currency'))
                        terms_lines.update({
                            'amount_currency': -total_amount_currency,
                            'debit': total_balance < 0.0 and -total_balance or 0.0,
                            'credit': total_balance > 0.0 and total_balance or 0.0,
                        })
                    if not already_exists and hasDiscount > 0:
                        print("Uni does not exist 1")
                        in_draft_mode = self != self._origin
                        # not in_draft_mode and 
                        if move.move_type == 'out_invoice':
                            
                            if hasDiscount and move.move_type in type_list:
                                in_draft_mode = self != self._origin
                                terms_lines = self.line_ids.filtered(
                                    lambda line: line.account_id.user_type_id.type in ('receivable', 'payable'))
                                already_exists = self.line_ids.filtered( lambda line: line.name and line.name.find(lineName) == 0)
                                if already_exists:
                                    print("Uni Aleady exisits 2 "+line.name + "should be"+ lineName)
                                    exists=True
                                    amount = universal_discount_line_amount
                                    if sale_uni_discount_account \
                                            and (self.move_type == "out_invoice"
                                                or self.move_type == "out_refund"):
                                        if self.move_type == "out_invoice":
                                            already_exists.update({
                                                'name': lineName,
                                                'debit': amount > 0.0 and amount or 0.0,
                                                'credit': amount < 0.0 and -amount or 0.0,
                                            })
                                        else:
                                            already_exists.update({
                                                'name': lineName,
                                                'debit': amount < 0.0 and -amount or 0.0,
                                                'credit': amount > 0.0 and amount or 0.0,
                                            })
                                        if  purchase_uni_discount_account\
                                                and (self.move_type == "in_invoice"
                                                    or self.move_type == "in_refund"):
                                            if self.move_type == "in_invoice":
                                                already_exists.update({
                                                    'name': lineName,
                                                    'debit': amount < 0.0 and -amount or 0.0,
                                                    'credit': amount > 0.0 and amount or 0.0,
                                                })
                                            else:
                                                already_exists.update({
                                                    'name': lineName,
                                                    'debit': amount > 0.0 and amount or 0.0,
                                                    'credit': amount < 0.0 and -amount or 0.0,
                                                })
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
                                    print("Uni does not exist 2")
                                    new_tax_line = self.env['account.move.line']
                                    create_method = in_draft_mode and \
                                                    self.env['account.move.line'].new or\
                                                    self.env['account.move.line'].create
                                    if sale_uni_discount_account \
                                            and (self.move_type == "out_invoice"
                                                or self.move_type == "out_refund"):
                                        amount = universal_discount_line_amount
                                        dict = {
                                            'move_name': move.name,
                                            'name':lineName,
                                            'move_id': move._origin,
                                            'product_id': line.product_id.id,
                                            'product_uom_id': line.product_uom_id.id,
                                            'quantity': 1,
                                            'price_unit': amount,
                                            'debit': amount > 0.0 and amount or 0.0,
                                            'credit': amount < 0.0 and -amount or 0.0,
                                            'account_id': sale_uni_discount_account,
                                            'analytic_account_id': line.analytic_account_id.id,
                                            'analytic_tag_ids': [(6, 0, line.analytic_tag_ids.ids)],
                                            'exclude_from_invoice_tab': True,
                                            'partner_id': terms_lines.partner_id.id,
                                            'company_id': terms_lines.company_id.id,
                                            'company_currency_id': terms_lines.company_currency_id.id,
                                            'date': move.date,
                                            }
                                        if move.move_type == "out_invoice":
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
                                            print("in Uni draft mode 1 sale")
                                            self.line_ids += create_method(dict)
                                            # Updation of Invoice Line Id
                                            duplicate_id = self.invoice_line_ids.filtered(
                                                lambda line: line.name and line.name.find(lineName) == 0)
                                            self.invoice_line_ids = self.invoice_line_ids - duplicate_id
                                        else:
                                            dict.update({
                                            'price_unit': 0.0,
                                            'debit': 0.0,
                                            'credit': 0.0,
                                                })
                                            self.line_ids = [(0, 0, dict)]

                                    if purchase_uni_discount_account\
                                            and (self.move_type == "in_invoice"
                                                or self.move_type == "in_refund"):
                                        amount = universal_discount_line_amount
                                        dict = {
                                            'move_name': move.name,
                                            'name':lineName,
                                            'move_id': move._origin,
                                            'product_id': line.product_id.id,
                                            'product_uom_id': line.product_uom_id.id,
                                            'quantity': 1,
                                            'price_unit': amount,
                                            'debit': amount > 0.0 and amount or 0.0,
                                            'credit': amount < 0.0 and -amount or 0.0,
                                            'account_id': purchase_uni_discount_account,
                                            'analytic_account_id': line.analytic_account_id.id,
                                            'analytic_tag_ids': [(6, 0, line.analytic_tag_ids.ids)],
                                            'exclude_from_invoice_tab': True,
                                            'partner_id': terms_lines.partner_id.id,
                                            'company_id': terms_lines.company_id.id,
                                            'company_currency_id': terms_lines.company_currency_id.id,
                                            'date': move.date,
                                            }

                                        if self.move_type == "in_invoice":
                                            dict.update({
                                                'debit': amount < 0.0 and -amount or 0.0,
                                                'credit': amount > 0.0 and amount or 0.0,
                                            })
                                        else:
                                            dict.update({
                                                'debit': amount > 0.0 and amount or 0.0,
                                                'credit': amount < 0.0 and -amount or 0.0,
                                            })
                                            self.line_ids += create_method(dict)
                                            # Updation of Invoice Line Id
                                            duplicate_id = self.invoice_line_ids.filtered(
                                                lambda line: line.name and line.name.find(lineName) == 0)
                                            self.invoice_line_ids = self.invoice_line_ids - duplicate_id
                                if in_draft_mode:
                                    print("Uni in draft mode 2")
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
                                    ipdb.set_trace()
                                else: 
                                    print("Uni not in draft mode final")
                                    already_exists = self.line_ids.filtered(
                                            lambda line: line.name and line.name.find(lineName) == 0)
                                    terms_lines = self.line_ids.filtered(
                                                        lambda line: line.account_id.user_type_id.type in ('receivable', 'payable'))
                                    other_lines = self.line_ids.filtered(
                                                        lambda line: line.account_id.user_type_id.type not in ('receivable', 'payable'))
                                    if(exists):
                                        total_balance = sum(other_lines.mapped('balance'))
                                    else:
                                        total_balance = sum(other_lines.mapped('balance')) + amount
                                    dict1 = {
                                            'debit': amount > 0.0 and amount or 0.0, 
                                            'credit': amount < 0.0 and -amount or 0.0,
                                            }
                                    dict2 = {
                                            'debit': total_balance < 0.0 and -total_balance or 0.0,
                                            'credit': total_balance > 0.0 and total_balance or 0.0,
                                    }
                                    print(self)
                                    # ipdb.set_trace()
                                    self.line_ids = [(1, already_exists.id, dict1), (1, terms_lines.id, dict2)] 
                                    print()

                            elif not hasDiscount:
                                print("Uni Does not have discount")
                                already_exists = self.line_ids.filtered(
                                    lambda line: line.name and line.name.find(lineName) == 0)
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

                    # Add discount line.
      
            # Post entries.
            # return super()._post(soft=False)
    @api.onchange('ks_global_discount_rate')
    def remove_lines_uni(self):
        print("checking lines to remove")
        for move in self:
            for line in move.invoice_line_ids:
                if move.ks_global_discount_rate == 0:
                    lineName =  line.name[:64]+" Universal discount "
                    already_exists = self.line_ids.filtered(
                                lambda line: line.name and line.name.find(lineName) == 0)
                    if already_exists:
                        print("found")
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

    def _prepare_analytic_line(self):
        res = super(YDSAccountMove, self)._prepare_analytic_line()
        for rec in self:
            res['ks_amount_discount'] = rec.ks_amount_discount
        return res
class KSAccountMoveLine(models.Model):
    _inherit = "account.move.line"

    # def unlink(self):
    #     print("unlink called")
    #     for line in self:
    #         lineName =  line.name[:64]+" Universal discount " + str(line.sequence)
    #         already_exists = self.filtered(
    #                         lambda line: line.name and line.name.find(lineName) == 0)
    #         if already_exists:
    #                 print("found")
    #                 self -= already_exists
    #                 terms_lines = self.filtered(
    #                     lambda line: line.account_id.user_type_id.type in ('receivable', 'payable'))
    #                 other_lines = self.filtered(
    #                     lambda line: line.account_id.user_type_id.type not in ('receivable', 'payable'))
    #                 total_balance = sum(other_lines.mapped('balance'))
    #                 total_amount_currency = sum(other_lines.mapped('amount_currency'))
    #                 terms_lines.update({
    #                     'amount_currency': -total_amount_currency,
    #                     'debit': total_balance < 0.0 and -total_balance or 0.0,
    #                     'credit': total_balance > 0.0 and total_balance or 0.0,
    #                 })
            
    #     res = super(KSAccountMoveLine, self).unlink()
    #     return res
class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    ks_amount_discount = fields.Float(string='Total Discount',readonly=True,store=True)