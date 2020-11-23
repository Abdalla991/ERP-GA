from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools.misc import formatLang


class KsGlobalDiscountInvoice(models.Model):
    # _inherit = "account.invoice"
    """ changing the model to account.move """
    _inherit = "account.move"


    ks_global_discount_type = fields.Selection([
                                                ('percent', 'Percentage'),
                                                ('amount', 'Amount')],
                                               string='Universal Discount Type',
                                               readonly=True,
                                                states={'draft': [('readonly', False)],
                                                        'sent': [('readonly', False)]},
                                                default='percent')
    ks_global_discount_rate = fields.Float('Universal Discount',
                                           readonly=True,
                                           states={'draft': [('readonly', False)],
                                                   'sent': [('readonly', False)]})
    ks_amount_discount = fields.Monetary(string='Universal Discount',
                                         readonly=True,
                                         compute='_compute_amount',
                                         store=True, track_visibility='always')
    ks_enable_discount = fields.Boolean(compute='ks_verify_discount')
    ks_sales_discount_account_id = fields.Integer(compute='ks_verify_discount')
    ks_purchase_discount_account_id = fields.Integer(compute='ks_verify_discount')

    @api.depends('company_id.ks_enable_discount')
    def ks_verify_discount(self):
        for rec in self:
            rec.ks_enable_discount = rec.company_id.ks_enable_discount
            rec.ks_sales_discount_account_id = rec.company_id.ks_sales_discount_account.id
            rec.ks_purchase_discount_account_id = rec.company_id.ks_purchase_discount_account.id

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



    # @api.depends(
    #     'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual',
    #     'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual_currency',
    #     'line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual',
    #     'line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual_currency',
    #     'line_ids.debit',
    #     'line_ids.credit',
    #     'line_ids.currency_id',
    #     'line_ids.amount_currency',
    #     'line_ids.amount_residual',
    #     'line_ids.amount_residual_currency',
    #     'line_ids.payment_id.state',
    #     'line_ids.full_reconcile_id')
    # def _compute_amount(self):
    #     for move in self:

    #         if move.payment_state == 'invoicing_legacy':
    #             # invoicing_legacy state is set via SQL when setting setting field
    #             # invoicing_switch_threshold (defined in account_accountant).
    #             # The only way of going out of this state is through this setting,
    #             # so we don't recompute it here.
    #             move.payment_state = move.payment_state
    #             continue

    #         total_untaxed = 0.0
    #         total_untaxed_currency = 0.0
    #         total_tax = 0.0
    #         total_tax_currency = 0.0
    #         total_to_pay = 0.0
    #         total_residual = 0.0
    #         total_residual_currency = 0.0
    #         total = 0.0
    #         total_currency = 0.0
    #         currencies = set()

    #         for line in move.line_ids:
    #             if line.currency_id:
    #                 currencies.add(line.currency_id)

    #             if move.is_invoice(include_receipts=True):
    #                 # === Invoices ===

    #                 if not line.exclude_from_invoice_tab:
    #                     # Untaxed amount.
    #                     total_untaxed += line.balance
    #                     total_untaxed_currency += line.amount_currency
    #                     total += line.balance
    #                     total_currency += line.amount_currency
    #                 elif line.tax_line_id:
    #                     # Tax amount.
    #                     total_tax += line.balance
    #                     total_tax_currency += line.amount_currency
    #                     total += line.balance
    #                     total_currency += line.amount_currency
    #                 elif line.account_id.user_type_id.type in ('receivable', 'payable'):
    #                     # Residual amount.
    #                     total_to_pay += line.balance
    #                     total_residual += line.amount_residual
    #                     total_residual_currency += line.amount_residual_currency
    #             else:
    #                 # === Miscellaneous journal entry ===
    #                 if line.debit:
    #                     total += line.balance
    #                     total_currency += line.amount_currency

    #         if move.move_type == 'entry' or move.is_outbound():
    #             sign = 1
    #         else:
    #             sign = -1
    #         move.amount_untaxed = sign * (total_untaxed_currency if len(currencies) == 1 else total_untaxed)
    #         move.amount_tax = sign * (total_tax_currency if len(currencies) == 1 else total_tax) * (1-move.ks_global_discount_rate/100)
    #         move.amount_total = sign * (total_currency if len(currencies) == 1 else total)
    #         move.amount_residual = -sign * (total_residual_currency if len(currencies) == 1 else total_residual)
    #         move.amount_untaxed_signed = -total_untaxed
    #         move.amount_untaxed_signed = -total_untaxed * (1-move.ks_global_discount_rate/100)
    #         move.amount_total_signed = abs(total) if move.move_type == 'entry' else -total
    #         move.amount_residual_signed = total_residual

    #         currency = len(currencies) == 1 and currencies.pop() or move.company_id.currency_id

    #         # Compute 'payment_state'.
    #         new_pmt_state = 'not_paid' if move.move_type != 'entry' else False

    #         if move.is_invoice(include_receipts=True) and move.state == 'posted':

    #             if currency.is_zero(move.amount_residual):
    #                 if all(payment.is_matched for payment in move._get_reconciled_payments()):
    #                     new_pmt_state = 'paid'
    #                 else:
    #                     new_pmt_state = move._get_invoice_in_payment_state()
    #             elif currency.compare_amounts(total_to_pay, total_residual) != 0:
    #                 new_pmt_state = 'partial'

    #         if new_pmt_state == 'paid' and move.move_type in ('in_invoice', 'out_invoice', 'entry'):
    #             reverse_type = move.move_type == 'in_invoice' and 'in_refund' or move.move_type == 'out_invoice' and 'out_refund' or 'entry'
    #             reverse_moves = self.env['account.move'].search([('reversed_entry_id', '=', move.id), ('state', '=', 'posted'), ('move_type', '=', reverse_type)])

    #             # We only set 'reversed' state in cas of 1 to 1 full reconciliation with a reverse entry; otherwise, we use the regular 'paid' state
    #             reverse_moves_full_recs = reverse_moves.mapped('line_ids.full_reconcile_id')
    #             if reverse_moves_full_recs.mapped('reconciled_line_ids.move_id').filtered(lambda x: x not in (reverse_moves + reverse_moves_full_recs.mapped('exchange_move_id'))) == move:
    #                 new_pmt_state = 'reversed'

    #         move.payment_state = new_pmt_state


    #         #universal discount edit 
    #         if not ('ks_global_tax_rate' in move):
    #             move.ks_calculate_discount()
    #         sign = move.move_type in ['in_refund', 'out_refund'] and -1 or 1
    #         move.amount_total_signed = move.amount_total * sign




    # @api.multi
    def ks_calculate_discount(self):
        for rec in self:
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
            #added line to solve the problem
            
            # rec.ks_amount_discount = rec.ks_amount_discount - rec.yds_total_discount
            rec.amount_total = rec.amount_tax + rec.amount_untaxed - rec.ks_amount_discount
            # rec.amount_untaxed -= rec.ks_amount_discount
            rec.amount_tax = rec.amount_tax * (1-rec.ks_global_discount_rate/100)
            rec.amount_tax_signed = rec.amount_tax_signed * (1-rec.ks_global_discount_rate/100)
            rec.yds_amount_total = rec.amount_tax + rec.yds_amount_untaxed_after_discount - rec.ks_amount_discount
            # rec.yds_amount_untaxed_after_discount -= rec.ks_amount_discount
            rec.ks_update_universal_discount()


    
    
    
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

    def ks_update_universal_discount(self):
        """This Function Updates the Universal Discount through Sale Order"""
        for rec in self:
            already_exists = self.line_ids.filtered(
                lambda line: line.name and line.name.find('Universal Discount') == 0)
            terms_lines = self.line_ids.filtered(
                lambda line: line.account_id.user_type_id.type in ('receivable', 'payable'))
            other_lines = self.line_ids.filtered(
                lambda line: line.account_id.user_type_id.type not in ('receivable', 'payable'))
            if already_exists:
                amount = rec.ks_amount_discount
                if rec.ks_sales_discount_account_id \
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
                if rec.ks_purchase_discount_account_id \
                        and (rec.move_type == "in_invoice"
                             or rec.move_type == "in_refund")\
                        and amount > 0:
                    if rec.move_type == "in_invoice":
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
            if not already_exists and rec.ks_global_discount_rate > 0:
                in_draft_mode = self != self._origin
                if not in_draft_mode and rec.move_type == 'out_invoice':
                    rec._recompute_universal_discount_lines()
                print()

    @api.onchange('ks_global_discount_rate', 'ks_global_discount_type', 'line_ids')
    def _recompute_universal_discount_lines(self):
        """This Function Create The General Entries for Universal Discount"""
        for rec in self:
            type_list = ['out_invoice', 'out_refund', 'in_invoice', 'in_refund']
            if rec.ks_global_discount_rate > 0 and rec.move_type in type_list:
                if rec.is_invoice(include_receipts=True):
                    in_draft_mode = self != self._origin
                    ks_name = "Universal Discount "
                    if rec.ks_global_discount_type == "amount":
                        ks_value = "of amount #" + str(self.ks_global_discount_rate)
                    elif rec.ks_global_discount_type == "percent":
                        ks_value = " @" + str(self.ks_global_discount_rate) + "%"
                    else:
                        ks_value = ''
                    ks_name = ks_name + ks_value
                    #           ("Invoice No: " + str(self.ids)
                    #            if self._origin.id
                    #            else (self.display_name))
                    terms_lines = self.line_ids.filtered(
                        lambda line: line.account_id.user_type_id.type in ('receivable', 'payable'))
                    already_exists = self.line_ids.filtered(
                                    lambda line: line.name and line.name.find('Universal Discount') == 0)
                    if already_exists:
                        amount = self.ks_amount_discount
                        if self.ks_sales_discount_account_id \
                                and (self.move_type == "out_invoice"
                                     or self.move_type == "out_refund"):
                            if self.move_type == "out_invoice":
                                already_exists.update({
                                    'name': ks_name,
                                    'debit': amount > 0.0 and amount or 0.0,
                                    'credit': amount < 0.0 and -amount or 0.0,
                                })
                            else:
                                already_exists.update({
                                    'name': ks_name,
                                    'debit': amount < 0.0 and -amount or 0.0,
                                    'credit': amount > 0.0 and amount or 0.0,
                                })
                        if self.ks_purchase_discount_account_id\
                                and (self.move_type == "in_invoice"
                                     or self.move_type == "in_refund"):
                            if self.move_type == "in_invoice":
                                already_exists.update({
                                    'name': ks_name,
                                    'debit': amount < 0.0 and -amount or 0.0,
                                    'credit': amount > 0.0 and amount or 0.0,
                                })
                            else:
                                already_exists.update({
                                    'name': ks_name,
                                    'debit': amount > 0.0 and amount or 0.0,
                                    'credit': amount < 0.0 and -amount or 0.0,
                                })
                    else:
                        new_tax_line = self.env['account.move.line']
                        create_method = in_draft_mode and \
                                        self.env['account.move.line'].new or\
                                        self.env['account.move.line'].create

                        if self.ks_sales_discount_account_id \
                                and (self.move_type == "out_invoice"
                                     or self.move_type == "out_refund"):
                            amount = self.ks_amount_discount
                            dict = {
                                    'move_name': self.name,
                                    'name': ks_name,
                                    'price_unit': self.ks_amount_discount,
                                    'quantity': 1,
                                    'debit': amount < 0.0 and -amount or 0.0,
                                    'credit': amount > 0.0 and amount or 0.0,
                                    'account_id': self.ks_sales_discount_account_id,
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
                                    lambda line: line.name and line.name.find('Universal Discount') == 0)
                                self.invoice_line_ids = self.invoice_line_ids - duplicate_id
                            else:
                                dict.update({
                                    'price_unit': 0.0,
                                    'debit': 0.0,
                                    'credit': 0.0,
                                })
                                self.line_ids = [(0, 0, dict)]

                        if self.ks_purchase_discount_account_id\
                                and (self.move_type == "in_invoice"
                                     or self.move_type == "in_refund"):
                            amount = self.ks_amount_discount
                            dict = {
                                    'move_name': self.name,
                                    'name': ks_name,
                                    'price_unit': self.ks_amount_discount,
                                    'quantity': 1,
                                    'debit': amount > 0.0 and amount or 0.0,
                                    'credit': amount < 0.0 and -amount or 0.0,
                                    'account_id': self.ks_purchase_discount_account_id,
                                    'move_id': self.id,
                                    'date': self.date,
                                    'exclude_from_invoice_tab': True,
                                    'partner_id': terms_lines.partner_id.id,
                                    'company_id': terms_lines.company_id.id,
                                    'company_currency_id': terms_lines.company_currency_id.id,
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
                            # updation of invoice line id
                            duplicate_id = self.invoice_line_ids.filtered(
                                lambda line: line.name and line.name.find('Universal Discount') == 0)
                            self.invoice_line_ids = self.invoice_line_ids - duplicate_id

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
                        terms_lines = self.line_ids.filtered(
                            lambda line: line.account_id.user_type_id.type in ('receivable', 'payable'))
                        other_lines = self.line_ids.filtered(
                            lambda line: line.account_id.user_type_id.type not in ('receivable', 'payable'))
                        already_exists = self.line_ids.filtered(
                            lambda line: line.name and line.name.find('Universal Discount') == 0)
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

            elif self.ks_global_discount_rate <= 0:
                already_exists = self.line_ids.filtered(
                    lambda line: line.name and line.name.find('Universal Discount') == 0)
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
        def _prepare_analytic_line(self):
            res = super(YDSAccountMove, self)._prepare_analytic_line()
            for rec in self:
                res['ks_amount_discount'] = rec.ks_amount_discount
            return res

class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    ks_amount_discount = fields.Float(string='Total Discount',readonly=True,store=True)