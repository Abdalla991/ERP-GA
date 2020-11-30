from odoo import models, fields, api, exceptions, _
from odoo.exceptions import UserError, ValidationError
import ipdb #Remove before publishing

#account.move -- account.move.line -- account.analytic.line

class YDSAccountMove(models.Model):
    _inherit = "account.move"

    #KS variables
    #########################################################################
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

    

    #Check that universal discount rate is valid
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
    
    #Add Universal discount lines per product
    def add_lines_uni(self):       
        # OVERRIDE
        # Don't change anything on moves used to cancel another ones.
        # return super()._post(soft=False)
        # print("add_lines for universal called")
        type_list = ['out_invoice', 'out_refund', 'in_invoice', 'in_refund']

        for move in self:
            count =0  #for counting loops
            if move.is_invoice(include_receipts=True):
                for line in move.invoice_line_ids:
                    count+=1
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
                        # print("line "+str(count)+"has "+"uni discount of " +str(universal_discount_line_amount))
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
                        # print("Uni Aleady exisits 1 "+line.name)
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
                        already_exists.update({
                                'analytic_account_id': line.analytic_account_id.id,
                            })
                        total_balance = sum(other_lines.mapped('balance'))
                        total_amount_currency = sum(other_lines.mapped('amount_currency'))
                        terms_lines.update({
                            'amount_currency': -total_amount_currency,
                            'debit': total_balance < 0.0 and -total_balance or 0.0,
                            'credit': total_balance > 0.0 and total_balance or 0.0,
                        })
                    if not already_exists and hasDiscount > 0:
                        # print("Uni does not exist 1")
                        in_draft_mode = self != self._origin
                        # not in_draft_mode and 
                        if move.move_type == 'out_invoice':
                            
                            if hasDiscount and move.move_type in type_list:
                                in_draft_mode = self != self._origin
                                terms_lines = self.line_ids.filtered(
                                    lambda line: line.account_id.user_type_id.type in ('receivable', 'payable'))
                                already_exists = self.line_ids.filtered( lambda line: line.name and line.name.find(lineName) == 0)
                                if already_exists:
                                    # print("Uni Aleady exisits 2 "+line.name + "should be"+ lineName)
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
                                    # print("Uni does not exist 2")
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
                                            # print("in Uni draft mode 1 sale")
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
                                    # print("Uni in draft mode 2")
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
                                    # print("Uni not in draft mode final")
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
                                    # ipdb.set_trace()
                                    self.line_ids = [(1, already_exists.id, dict1), (1, terms_lines.id, dict2)] 
                                    print()

                            elif not hasDiscount:
                                # print("Uni Does not have discount")
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

  
    #Remove Universal discount lines if rate == 0

    @api.onchange('ks_global_discount_rate')
    def remove_lines_uni(self):
        # print("checking lines to remove")
        for move in self:
            for line in move.invoice_line_ids:
                if move.ks_global_discount_rate == 0:
                    lineName =  line.name[:64]+" Universal discount "
                    already_exists = self.line_ids.filtered(
                                lambda line: line.name and line.name.find(lineName) == 0)
                    if already_exists:
                        # print("found")
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


    # YDS regular discount related variables
    #########################################################################
    yds_total_discount = fields.Float(string='Total Discount',readonly=True,store=True)
    yds_pricelist_account_id = fields.Integer(string='Pricelist account ID',  readonly=True,store=True)
    yds_pricelist_name = fields.Char(string ='Pricelist Name',readonly=True,store=True)
    yds_amount_untaxed = fields.Monetary(string='Untaxed Amount', store=True, readonly=True, currency_field='company_currency_id')
    yds_amount_untaxed_after_discount = fields.Monetary(string='Untaxed Amount After Discount', store=True, readonly=True, currency_field='company_currency_id')
    yds_is_sales_order = fields.Boolean(string="is Sales Order")
    yds_amount_tax = fields.Monetary(string='Tax', store=True, readonly=True)
    #pricelist_related_fields
    #added because of the change in pricelist subtotal
    # yds_amount_total = fields.Monetary(string='Total', store=True, readonly=True, compute='_compute_amount2')
    @api.onchange(
        'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual',
        'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual_currency',
        'line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual',
        'line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual_currency', 
        'line_ids.debit',
        'line_ids.credit',
        'line_ids.currency_id',
        'line_ids.amount_currency',
        'line_ids.amount_residual',
        'line_ids.amount_residual_currency',
        'line_ids.payment_id.state',
        'line_ids.full_reconcile_id',
        'line_ids.price_subtotal',
        'line_ids.analytic_account_id'
        'yds_total_discount',
        'ks_global_discount_rate',
        'pricelist_id',
        'ks_global_discount_type',
        'partner_id',
        'invoice_line_ids.discount')
    def _compute_amount(self):
            for move in self:
                if move.payment_state == 'invoicing_legacy':
                    # invoicing_legacy state is set via SQL when setting setting field
                    # invoicing_switch_threshold (defined in account_accountant).
                    # The only way of going out of this state is through this setting,
                    # so we don't recompute it here.
                    move.payment_state = move.payment_state
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


                
                move._recompute_tax_lines()
                for line in move.line_ids:
                    if line.currency_id:
                        currencies.add(line.currency_id)

                    if move.is_invoice(include_receipts=True):
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

                if move.move_type == 'entry' or move.is_outbound():
                    sign = 1
                else:
                    sign = -1


                 
                
                # move.amount_tax = move.amount_tax - invoiceTaxForUniversalDiscount ###
                # difference = move.yds_amount_tax - move.amount_tax
                
                # move.amount_total = sign * (total_currency if len(currencies) == 1 else total) - move.yds_total_discount - move.ks_amount_discount - difference ###
                
                # move.amount_total = sign * (total_currency if len(currencies) == 1 else total)
                
                # move.amount_residual = -sign * (total_residual_currency if len(currencies) == 1 else total_residual) - difference  ###
                # move.amount_untaxed_signed = -total_untaxed
                # # move.amount_tax_signed = -total_tax * (1-move.ks_global_discount_rate/100) ####
                # move.amount_tax_signed = -total_tax
                # move.amount_total_signed = abs(total) if move.move_type == 'entry' else -total
                # move.amount_residual_signed = total_residual

                # move.yds_amount_tax = move.amount_tax

             



                
                move.amount_untaxed = sign * (total_untaxed_currency if len(currencies) == 1 else total_untaxed)
                move.amount_tax = sign * (total_tax_currency if len(currencies) == 1 else total_tax)
                move.amount_untaxed_signed = -total_untaxed
                move.amount_tax_signed = -total_tax

                move.yds_total_discount=0
                move._calculatePricelistDiscount()
                move.yds_amount_untaxed = move.amount_untaxed
                move.yds_amount_untaxed_after_discount = move.yds_amount_untaxed - move.yds_total_discount

                if move.ks_global_discount_type == "percent":
                    if move.ks_global_discount_rate != 0.0:
                        move.ks_amount_discount = (move.yds_amount_untaxed_after_discount) * move.ks_global_discount_rate / 100
                    else:
                        move.ks_amount_discount = 0
                elif not move.ks_global_discount_type:
                    move.ks_global_discount_rate = 0
                    move.ks_amount_discount = 0


                
                move.amount_total = sign * (total_currency if len(currencies) == 1 else total) - move.yds_total_discount - move.ks_amount_discount
                move.amount_residual = -sign * (total_residual_currency if len(currencies) == 1 else total_residual)
                move.amount_total_signed = abs(total) if move.move_type == 'entry' else -total- move.yds_total_discount - move.ks_amount_discount
                move.amount_residual_signed = total_residual
                # invoiceTaxForDiscount = 0
                # invoiceTaxForUniversalDiscount = 0
                # invoiceTaxForProduct = 0
                # for line in move.invoice_line_ids:
                #     discount_amount = line.yds_price_subtotal * line.discount / 100
                #     universal_discount_amount = line.yds_price_subtotal * (1-line.discount / 100) * move.ks_global_discount_rate / 100
                #     totalTax = 0
                #     for tax in line.tax_ids:
                #         totalTax += tax.amount
                #     taxForDiscount = discount_amount * totalTax /100
                #     taxForUniversalDiscount = universal_discount_amount * totalTax /100
                #     taxForProduct = line.yds_price_subtotal * totalTax /100
                #     invoiceTaxForDiscount += taxForDiscount
                #     invoiceTaxForUniversalDiscount += taxForUniversalDiscount
                #     invoiceTaxForProduct += taxForProduct
                #     print("----------Moataz Start---------")
                #     print ("Invoice tax "+ str(invoiceTaxForDiscount))
                #     print ("universal Invoice tax "+ str(invoiceTaxForUniversalDiscount))
                #     print ("total product Tax: "+ str(invoiceTaxForProduct))     

                # if invoiceTaxForProduct ==  sign * (total_tax_currency if len(currencies) == 1 else total_tax):
                #     move.amount_tax = invoiceTaxForProduct - invoiceTaxForDiscount
                # else:
                #     move.amount_tax = sign * (total_tax_currency if len(currencies) == 1 else total_tax)

                
                # print("amount_tax" + str(move.amount_tax))
                # print("----------Moataz End---------")


                

                move.add_lines_uni()
                move.add_lines()
                move._recompute_tax_lines()


                currency = len(currencies) == 1 and currencies.pop() or move.company_id.currency_id

                # Compute 'payment_state'.
                new_pmt_state = 'not_paid' if move.move_type != 'entry' else False

                if move.is_invoice(include_receipts=True) and move.state == 'posted':

                    if currency.is_zero(move.amount_residual):
                        if all(payment.is_matched for payment in move._get_reconciled_payments()):
                            new_pmt_state = 'paid'
                        else:
                            new_pmt_state = move._get_invoice_in_payment_state()
                    elif currency.compare_amounts(total_to_pay, total_residual) != 0:
                        new_pmt_state = 'partial'

                if new_pmt_state == 'paid' and move.move_type in ('in_invoice', 'out_invoice', 'entry'):
                    reverse_type = move.move_type == 'in_invoice' and 'in_refund' or move.move_type == 'out_invoice' and 'out_refund' or 'entry'
                    reverse_moves = self.env['account.move'].search([('reversed_entry_id', '=', move.id), ('state', '=', 'posted'), ('move_type', '=', reverse_type)])

                    # We only set 'reversed' state in cas of 1 to 1 full reconciliation with a reverse entry; otherwise, we use the regular 'paid' state
                    reverse_moves_full_recs = reverse_moves.mapped('line_ids.full_reconcile_id')
                    if reverse_moves_full_recs.mapped('reconciled_line_ids.move_id').filtered(lambda x: x not in (reverse_moves + reverse_moves_full_recs.mapped('exchange_move_id'))) == move:
                        new_pmt_state = 'reversed'

                move.payment_state = new_pmt_state

    

    #Rename lines with same already existing product to avoid ignoring of discount lines due to dubplicate line names
    @api.onchange('invoice_line_ids')
    def rename_line(self):
        # print("rename_lines")
        productNames = [] 
        productCounts = []
        for rec in self :
            innerloopCount=0
            for line in rec.invoice_line_ids:
                # print("line number: " + str(innerloopCount))
                innerloopCount+=1
                # print(line.product_id.name)
                if line.product_id.name in productNames:
                    # print("product found") 
                    index = productNames.index(line.product_id.name)
                    productCounts[index]+=1
                    line.name = line.product_id.name +" ("+str(productCounts[index])+")"
                    # print(line.name) 
                else:   
                    # print("product not found..adding new product")
                    productNames.append(line.product_id.name)
                    productCounts.append(1)
                    # print(productNames)
                    # print(productCounts)

    #On row deletion or addition readd lines
    # @api.onchange('invoice_line_ids')
    def reInsert_lines(self):
        print("reInsert_lines called")
        for move in self:
            for line in move.line_ids:
                if line.name:
                    if "discount" in line.name:
                        self.line_ids -= line
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
            move.add_lines()
            
    

    #Calculate yds_total_discount
    def _calculatePricelistDiscount(self):
        for rec in self:
            for line in rec.line_ids:
                rec.yds_total_discount += line.price_unit * ( (line.discount or 0.0) / 100.0) * line.quantity
            
            
    
    @api.model
    def _prepare_refund(self, invoice, date_invoice=None, date=None, description=None, journal_id=None):
        yds_res = super(YDSAccountMove, self)._prepare_refund(invoice, date_invoice=None, date=None,
                                                                      description=None, journal_id=None)
        yds_res['yds_total_discount'] = self.yds_total_discount
        return yds_res



    # #Add regular discount line per product
    # @api.onchange('line_ids.discount',
    #     'line_ids.price_subtotal',
    #     'yds_total_discount')
    def add_lines(self):       
        type_list = ['out_invoice', 'out_refund', 'in_invoice', 'in_refund']
        for move in self:
            count =0  #for counting loops
            if move.is_invoice(include_receipts=True):
                for line in move.invoice_line_ids:
                    count+=1
                    print("adding discount line for invoice line: "+str(count))

                    # print(count)
                    exists = False
                    # Filter out lines being not eligible for discount/universal discount line.
                    if line.product_id.type != 'product' or line.product_id.valuation != 'real_time':
                        continue

                    product_discount_account = move.pricelist_id.yds_assigned_discount_account.id
                    # unversal_discount_account = accounts['expense'] or self.journal_id.default_account_id
                    if not product_discount_account:  #or not unversal_discount_account:
                        continue

                    sign = -1 if move.move_type == 'out_refund' else 1
                    # price_unit = line.price_unit
                    # balance = sign * line.quantity * price_unit

                    #Calculations
                    uni_discount_rate=move.ks_global_discount_rate
                    amount = ((line.credit or 0.0) - (line.debit or 0.0))*sign
                    pricelist_discount_line_amount =(line.price_unit * ( (line.discount or 0.0) / 100.0) *line.quantity)

                    hasDiscount = pricelist_discount_line_amount > 0

                    if(uni_discount_rate>0):
                        universal_discount_line_amount = ((amount-pricelist_discount_line_amount)/uni_discount_rate)
                    else:
                        universal_discount_line_amount=0

                    
                    lineName = line.name[:64]+" discount "
                    already_exists = self.line_ids.filtered(
                        lambda line: line.name and line.name.find(lineName) == 0)
                    terms_lines = self.line_ids.filtered(
                        lambda line: line.account_id.user_type_id.type in ('receivable', 'payable'))
                    other_lines = self.line_ids.filtered(
                        lambda line: line.account_id.user_type_id.type not in ('receivable', 'payable'))
                    if pricelist_discount_line_amount > 0 :
                        if already_exists:
                            print("Aleady exisits 1 "+line.name)
                            exists=True
                            amount = pricelist_discount_line_amount
                            print("new amount = "+str(amount))
                            if product_discount_account \
                                    and (move.move_type == "out_invoice"
                                        or move.move_type == "out_refund"):
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
                                already_exists.update({
                                    'analytic_account_id': line.analytic_account_id.id,
                                })
                            total_balance = sum(other_lines.mapped('balance'))
                            total_amount_currency = sum(other_lines.mapped('amount_currency'))
                            terms_lines.update({
                                'amount_currency': -total_amount_currency,
                                'debit': total_balance < 0.0 and -total_balance or 0.0,
                                'credit': total_balance > 0.0 and total_balance or 0.0,
                                'price_unit': total_balance,
                            })
                            print("total_balance= " + str(total_balance))
                            # ipdb.set_trace()
                        if not already_exists and pricelist_discount_line_amount > 0:
                            print("does not exist")
                            in_draft_mode = self != self._origin
                            if move.move_type == 'out_invoice':
                                newLineName = line.name[:64]+" discount "
                                if hasDiscount and move.move_type in type_list:
                                    in_draft_mode = self != self._origin
                                    terms_lines = self.line_ids.filtered(
                                        lambda line: line.account_id.user_type_id.type in ('receivable', 'payable'))
                                    already_exists = self.line_ids.filtered( lambda line: line.name and line.name.find(newLineName) == 0)
                                    if already_exists:
                                        print("Aleady exisits 2 "+line.name + "should be"+ newLineName)
                                        exists=True
                                        amount = pricelist_discount_line_amount
                                        if product_discount_account \
                                                and (self.move_type == "out_invoice"
                                                    or self.move_type == "out_refund"):
                                            if self.move_type == "out_invoice":
                                                already_exists.update({
                                                    'name': newLineName,
                                                    'debit': amount > 0.0 and amount or 0.0,
                                                    'credit': amount < 0.0 and -amount or 0.0,
                                                })
                                            else:
                                                already_exists.update({
                                                    'name': newLineName,
                                                    'debit': amount < 0.0 and -amount or 0.0,
                                                    'credit': amount > 0.0 and amount or 0.0,
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
                                                    'price_unit': total_balance,
                                                    
                                                })
                                    else:
                                        print("does not exist 2")
                                        new_tax_line = self.env['account.move.line']
                                        create_method = in_draft_mode and \
                                                        self.env['account.move.line'].new or\
                                                        self.env['account.move.line'].create
                                        if product_discount_account \
                                                and (self.move_type == "out_invoice"
                                                    or self.move_type == "out_refund"):
                                            amount = pricelist_discount_line_amount
                                            dict = {
                                                'move_name': move.name,
                                                'name':newLineName,
                                                'move_id': move._origin,
                                                'product_id': line.product_id.id,
                                                'product_uom_id': line.product_uom_id.id,
                                                'quantity': 1,
                                                'price_unit': pricelist_discount_line_amount,
                                                'debit': pricelist_discount_line_amount > 0.0 and pricelist_discount_line_amount or 0.0,
                                                'credit': pricelist_discount_line_amount < 0.0 and -pricelist_discount_line_amount or 0.0,
                                                'account_id': product_discount_account,
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
                                                'debit': pricelist_discount_line_amount > 0.0 and pricelist_discount_line_amount or 0.0,
                                                'credit': pricelist_discount_line_amount < 0.0 and -pricelist_discount_line_amount or 0.0,
                                                })
                                            else:
                                                dict.update({
                                                    'debit': pricelist_discount_line_amount < 0.0 and -pricelist_discount_line_amount or 0.0,
                                                    'credit': pricelist_discount_line_amount > 0.0 and pricelist_discount_line_amount or 0.0,
                                                })
                                            if in_draft_mode:
                                                print("in draft mode 1")
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
                                    if in_draft_mode:
                                        print("in draft mode 2")
                                        # Update the payement account amount
                                        terms_lines = self.line_ids.filtered(
                                            lambda line: line.account_id.user_type_id.type in ('receivable', 'payable'))
                                        other_lines = self.line_ids.filtered(
                                            lambda line: line.account_id.user_type_id.type not in ('receivable', 'payable'))
                                        total_balance = sum(other_lines.mapped('balance'))  
                                        print("total balance: "+ str(total_balance))
                                        total_amount_currency = sum(other_lines.mapped('amount_currency'))
                                        print("exists? " + str(exists))
                                        if(exists):
                                            total_balance = sum(other_lines.mapped('balance'))
                                        else:
                                            total_balance = sum(other_lines.mapped('balance')) 
                                        terms_lines.update({
                                            'amount_currency': -total_amount_currency,
                                            'debit': total_balance < 0.0 and -total_balance or 0.0,
                                            'credit': total_balance > 0.0 and total_balance or 0.0,
                                            'price_unit': total_balance,
                                            })
                                    else: 
                                        print("not in draft mode final")
                                        already_exists = self.line_ids.filtered(
                                                lambda line: line.name and line.name.find(newLineName) == 0)
                                        terms_lines = self.line_ids.filtered(
                                                            lambda line: line.account_id.user_type_id.type in ('receivable', 'payable'))
                                        other_lines = self.line_ids.filtered(
                                                            lambda line: line.account_id.user_type_id.type not in ('receivable', 'payable'))
                                        total_balance = sum(other_lines.mapped('balance'))  
                                        total_amount_currency = sum(other_lines.mapped('amount_currency'))
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
                                        # ipdb.set_trace()
                                        self.line_ids = [(1, already_exists.id, dict1), (1, terms_lines.id, dict2)] 
                        
                                        print()
                            


    #Remove regular discount line per product when discount == 0
    @api.onchange('invoice_line_ids')
    def remove_lines_disc(self):
        print("checking lines to remove")
        for move in self:
            for line in move.invoice_line_ids:
                if line.discount == 0:
                    lineName = line.name[:64]+" discount "
                    already_exists = self.line_ids.filtered(
                                lambda line: line.name and line.name.find(lineName) == 0)
                    if already_exists:
                        print("found and removing: "+already_exists.name)
                        # ipdb.set_trace()
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
                            'price_unit': total_balance,
                        })
                        # self.line_ids = [(1, already_exists.id, dict1), (1, terms_lines.id, dict2)] 
    
  
 
    def _check_balanced(self):
        ''' Assert the move is fully balanced debit = credit.
        An error is raised if it's not the case.
        '''
        moves = self.filtered(lambda move: move.line_ids)
        if not moves:
            return
        for move in self:
            for line in move.line_ids:
                print ("Line Name: "+str(line.name)+"--- credit: "+str(line.credit)+" - "+"debit: "+ str(line.debit))    

        # /!\ As this method is called in create / write, we can't make the assumption the computed stored fields
        # are already done. Then, this query MUST NOT depend of computed stored fields (e.g. balance).
        # It happens as the ORM makes the create with the 'no_recompute' statement.
        self.env['account.move.line'].flush(self.env['account.move.line']._fields)
        self.env['account.move'].flush(['journal_id'])
        self._cr.execute('''
            SELECT line.move_id, ROUND(SUM(line.debit - line.credit), currency.decimal_places)
            FROM account_move_line line
            JOIN account_move move ON move.id = line.move_id
            JOIN account_journal journal ON journal.id = move.journal_id
            JOIN res_company company ON company.id = journal.company_id
            JOIN res_currency currency ON currency.id = company.currency_id
            WHERE line.move_id IN %s
            GROUP BY line.move_id, currency.decimal_places
            HAVING ROUND(SUM(line.debit - line.credit), currency.decimal_places) != 0.0;
        ''', [tuple(self.ids)])

        query_res = self._cr.fetchall()
        if query_res:
            # ipdb.set_trace()
            ids = [res[0] for res in query_res]
            sums = [res[1] for res in query_res]
            raise UserError(_("Cannot create unbalanced journal entry. Ids: %s\nDifferences debit - credit: %s") % (ids, sums))

    def _recompute_tax_lines(self, recompute_tax_base_amount=False):
        ''' Compute the dynamic tax lines of the journal entry.

        :param lines_map: The line_ids dispatched by type containing:
            * base_lines: The lines having a tax_ids set.
            * tax_lines: The lines having a tax_line_id set.
            * terms_lines: The lines generated by the payment terms of the invoice.
            * rounding_lines: The cash rounding lines of the invoice.
        '''
        self.ensure_one()
        in_draft_mode = self != self._origin

        def _serialize_tax_grouping_key(grouping_dict):
            ''' Serialize the dictionary values to be used in the taxes_map.
            :param grouping_dict: The values returned by '_get_tax_grouping_key_from_tax_line' or '_get_tax_grouping_key_from_base_line'.
            :return: A string representing the values.
            '''
            return '-'.join(str(v) for v in grouping_dict.values())

        def _compute_base_line_taxes(base_line):
            ''' Compute taxes amounts both in company currency / foreign currency as the ratio between
            amount_currency & balance could not be the same as the expected currency rate.
            The 'amount_currency' value will be set on compute_all(...)['taxes'] in multi-currency.
            :param base_line:   The account.move.line owning the taxes.
            :return:            The result of the compute_all method.
            '''
            move = base_line.move_id

            if move.is_invoice(include_receipts=True):
                handle_price_include = True
                sign = -1 if move.is_inbound() else 1
                quantity = base_line.quantity
                is_refund = move.move_type in ('out_refund', 'in_refund')
                price_unit_wo_discount = sign * base_line.price_unit * (1 - (base_line.discount / 100.0))*(1 - (move.ks_global_discount_rate / 100)) 
            else:
                handle_price_include = False
                quantity = 1.0
                tax_type = base_line.tax_ids[0].type_tax_use if base_line.tax_ids else None
                is_refund = (tax_type == 'sale' and base_line.debit) or (tax_type == 'purchase' and base_line.credit)
                price_unit_wo_discount = base_line.balance

            balance_taxes_res = base_line.tax_ids._origin.compute_all(
                price_unit_wo_discount,
                currency=base_line.currency_id,
                quantity=quantity,
                product=base_line.product_id,
                partner=base_line.partner_id,
                is_refund=is_refund,
                handle_price_include=handle_price_include,
            )

            if move.move_type == 'entry':
                repartition_field = is_refund and 'refund_repartition_line_ids' or 'invoice_repartition_line_ids'
                repartition_tags = base_line.tax_ids.mapped(repartition_field).filtered(lambda x: x.repartition_type == 'base').tag_ids
                tags_need_inversion = (tax_type == 'sale' and not is_refund) or (tax_type == 'purchase' and is_refund)
                if tags_need_inversion:
                    balance_taxes_res['base_tags'] = base_line._revert_signed_tags(repartition_tags).ids
                    for tax_res in balance_taxes_res['taxes']:
                        tax_res['tag_ids'] = base_line._revert_signed_tags(self.env['account.account.tag'].browse(tax_res['tag_ids'])).ids

            return balance_taxes_res

        taxes_map = {}

        # ==== Add tax lines ====
        to_remove = self.env['account.move.line']
        for line in self.line_ids.filtered('tax_repartition_line_id'):
            grouping_dict = self._get_tax_grouping_key_from_tax_line(line)
            grouping_key = _serialize_tax_grouping_key(grouping_dict)
            if grouping_key in taxes_map:
                # A line with the same key does already exist, we only need one
                # to modify it; we have to drop this one.
                to_remove += line
            else:
                taxes_map[grouping_key] = {
                    'tax_line': line,
                    'amount': 0.0,
                    'tax_base_amount': 0.0,
                    'grouping_dict': False,
                }
        self.line_ids -= to_remove

        # ==== Mount base lines ====
        for line in self.line_ids.filtered(lambda line: not line.tax_repartition_line_id):
            # Don't call compute_all if there is no tax.
            if not line.tax_ids:
                line.tax_tag_ids = [(5, 0, 0)]
                continue

            compute_all_vals = _compute_base_line_taxes(line)

            # Assign tags on base line
            line.tax_tag_ids = compute_all_vals['base_tags']

            tax_exigible = True
            for tax_vals in compute_all_vals['taxes']:
                grouping_dict = self._get_tax_grouping_key_from_base_line(line, tax_vals)
                grouping_key = _serialize_tax_grouping_key(grouping_dict)

                tax_repartition_line = self.env['account.tax.repartition.line'].browse(tax_vals['tax_repartition_line_id'])
                tax = tax_repartition_line.invoice_tax_id or tax_repartition_line.refund_tax_id

                if tax.tax_exigibility == 'on_payment':
                    tax_exigible = False

                taxes_map_entry = taxes_map.setdefault(grouping_key, {
                    'tax_line': None,
                    'amount': 0.0,
                    'tax_base_amount': 0.0,
                    'grouping_dict': False,
                })
                taxes_map_entry['amount'] += tax_vals['amount']
                taxes_map_entry['tax_base_amount'] += self._get_base_amount_to_display(tax_vals['base'], tax_repartition_line)
                taxes_map_entry['grouping_dict'] = grouping_dict
            line.tax_exigible = tax_exigible

        # ==== Process taxes_map ====
        for taxes_map_entry in taxes_map.values():
            # The tax line is no longer used in any base lines, drop it.
            if taxes_map_entry['tax_line'] and not taxes_map_entry['grouping_dict']:
                self.line_ids -= taxes_map_entry['tax_line']
                continue

            currency = self.env['res.currency'].browse(taxes_map_entry['grouping_dict']['currency_id'])

            # Don't create tax lines with zero balance.
            if currency.is_zero(taxes_map_entry['amount']):
                if taxes_map_entry['tax_line']:
                    self.line_ids -= taxes_map_entry['tax_line']
                continue

            # tax_base_amount field is expressed using the company currency.
            tax_base_amount = currency._convert(taxes_map_entry['tax_base_amount'], self.company_currency_id, self.company_id, self.date or fields.Date.context_today(self))

            # Recompute only the tax_base_amount.
            if taxes_map_entry['tax_line'] and recompute_tax_base_amount:
                taxes_map_entry['tax_line'].tax_base_amount = tax_base_amount
                continue

            balance = currency._convert(
                taxes_map_entry['amount'],
                self.journal_id.company_id.currency_id,
                self.journal_id.company_id,
                self.date or fields.Date.context_today(self),
            )
            to_write_on_line = {
                'amount_currency': taxes_map_entry['amount'],
                'currency_id': taxes_map_entry['grouping_dict']['currency_id'],
                'debit': balance > 0.0 and balance or 0.0,
                'credit': balance < 0.0 and -balance or 0.0,
                'tax_base_amount': tax_base_amount,
            }

            if taxes_map_entry['tax_line']:
                # Update an existing tax line.
                taxes_map_entry['tax_line'].update(to_write_on_line)
            else:
                create_method = in_draft_mode and self.env['account.move.line'].new or self.env['account.move.line'].create
                tax_repartition_line_id = taxes_map_entry['grouping_dict']['tax_repartition_line_id']
                tax_repartition_line = self.env['account.tax.repartition.line'].browse(tax_repartition_line_id)
                tax = tax_repartition_line.invoice_tax_id or tax_repartition_line.refund_tax_id
                taxes_map_entry['tax_line'] = create_method({
                    **to_write_on_line,
                    'name': tax.name,
                    'move_id': self.id,
                    'partner_id': line.partner_id.id,
                    'company_id': line.company_id.id,
                    'company_currency_id': line.company_currency_id.id,
                    'tax_base_amount': tax_base_amount,
                    'exclude_from_invoice_tab': True,
                    'tax_exigible': tax.tax_exigibility == 'on_invoice',
                    **taxes_map_entry['grouping_dict'],
                })

            if in_draft_mode:
                taxes_map_entry['tax_line'].update(taxes_map_entry['tax_line']._get_fields_onchange_balance(force_computation=True))

class YDSAccountMoveLine(models.Model):
    _inherit = "account.move.line"
    yds_price_subtotal = fields.Monetary(string='Subtotal', store=True, readonly=True, currency_field='currency_id')
    yds_price_total = fields.Monetary(string='Total', store=True, readonly=True,currency_field='currency_id')

    @api.model
    @api.onchange('move_id.ks_global_discount_rate')
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
            
            res['price_subtotal'] = taxes_res['total_excluded']/(1 - (discount / 100.0)) 
            res['price_total'] = taxes_res['total_included']/(1 - (discount / 100.0))
            #change res['debit']
            res['yds_price_subtotal'] = taxes_res['total_excluded'] 
            res['yds_price_total'] = taxes_res['total_included']
        else:
            res['price_total'] = res['price_subtotal'] = subtotal
            res['yds_price_total'] = res['yds_price_subtotal'] = yds_subtotal
        #In case of multi currency, round before it's use for computing debit credit
        if currency:
            res = {k: currency.round(v) for k, v in res.items()}
        return res
    def write(self, vals):
        # OVERRIDE
        ACCOUNTING_FIELDS = ('debit', 'credit', 'amount_currency')
        BUSINESS_FIELDS = ('price_unit', 'quantity', 'discount', 'tax_ids')
        PROTECTED_FIELDS_TAX_LOCK_DATE = ['debit', 'credit', 'tax_line_id', 'tax_ids', 'tax_tag_ids']
        PROTECTED_FIELDS_LOCK_DATE = PROTECTED_FIELDS_TAX_LOCK_DATE + ['account_id', 'journal_id', 'amount_currency', 'currency_id', 'partner_id']
        PROTECTED_FIELDS_RECONCILIATION = ('account_id', 'date', 'debit', 'credit', 'amount_currency', 'currency_id')
        
        account_to_write = self.env['account.account'].browse(vals['account_id']) if 'account_id' in vals else None

        # Check writing a deprecated account.
        if account_to_write and account_to_write.deprecated:
            raise UserError(_('You cannot use a deprecated account.'))

        for line in self:
            if line.parent_state == 'posted':
                if line.move_id.restrict_mode_hash_table and set(vals).intersection(INTEGRITY_HASH_LINE_FIELDS):
                    raise UserError(_("You cannot edit the following fields due to restrict mode being activated on the journal: %s.") % ', '.join(INTEGRITY_HASH_LINE_FIELDS))
                if any(key in vals for key in ('tax_ids', 'tax_line_ids')):
                    raise UserError(_('You cannot modify the taxes related to a posted journal item, you should reset the journal entry to draft to do so.'))

            # Check the lock date.
            if any(self.env['account.move']._field_will_change(line, vals, field_name) for field_name in PROTECTED_FIELDS_LOCK_DATE):
                line.move_id._check_fiscalyear_lock_date()

            # Check the tax lock date.
            if any(self.env['account.move']._field_will_change(line, vals, field_name) for field_name in PROTECTED_FIELDS_TAX_LOCK_DATE):
                line._check_tax_lock_date()

            # Check the reconciliation.
            if any(self.env['account.move']._field_will_change(line, vals, field_name) for field_name in PROTECTED_FIELDS_RECONCILIATION):
                line._check_reconciliation()

            # Check switching receivable / payable accounts.
            if account_to_write:
                account_type = line.account_id.user_type_id.type
                if line.move_id.is_sale_document(include_receipts=True):
                    if (account_type == 'receivable' and account_to_write.user_type_id.type != account_type) \
                            or (account_type != 'receivable' and account_to_write.user_type_id.type == 'receivable'):
                        raise UserError(_("You can only set an account having the receivable type on payment terms lines for customer invoice."))
                if line.move_id.is_purchase_document(include_receipts=True):
                    if (account_type == 'payable' and account_to_write.user_type_id.type != account_type) \
                            or (account_type != 'payable' and account_to_write.user_type_id.type == 'payable'):
                        raise UserError(_("You can only set an account having the payable type on payment terms lines for vendor bill."))

        # Get all tracked fields (without related fields because these fields must be manage on their own model)
        tracking_fields = []
        for value in vals:
            field = self._fields[value]
            if hasattr(field, 'related') and field.related:
                continue # We don't want to track related field.
            if hasattr(field, 'tracking') and field.tracking:
                tracking_fields.append(value)
        ref_fields = self.env['account.move.line'].fields_get(tracking_fields)

        # Get initial values for each line
        move_initial_values = {}
        for line in self.filtered(lambda l: l.move_id.posted_before): # Only lines with posted once move.
            for field in tracking_fields:
                # Group initial values by move_id
                if line.move_id.id not in move_initial_values:
                    move_initial_values[line.move_id.id] = {}
                move_initial_values[line.move_id.id].update({field: line[field]})

        # Create the dict for the message post
        tracking_values = {} # Tracking values to write in the message post
        for move_id, modified_lines in move_initial_values.items():
            tmp_move = {move_id: []}
            for line in self.filtered(lambda l: l.move_id.id == move_id):
                changes, tracking_value_ids = line._mail_track(ref_fields, modified_lines) # Return a tuple like (changed field, ORM command)
                tmp = {'line_id': line.id}
                if tracking_value_ids:
                    selected_field = tracking_value_ids[0][2] # Get the last element of the tuple in the list of ORM command. (changed, [(0, 0, THIS)])
                    tmp.update({
                        **{'field_name': selected_field.get('field_desc')},
                        **self._get_formated_values(selected_field)
                    })
                elif changes:
                    field_name = line._fields[changes.pop()].string # Get the field name
                    tmp.update({
                        'error': True,
                        'field_error': field_name
                    })
                else:
                    continue
                tmp_move[move_id].append(tmp)
            if len(tmp_move[move_id]) > 0:
                tracking_values.update(tmp_move)
        # Write in the chatter.
        for move in self.mapped('move_id'):
            fields = tracking_values.get(move.id, [])
            if len(fields) > 0:
                msg = self._get_tracking_field_string(tracking_values.get(move.id))
                move.message_post(body=msg) # Write for each concerned move the message in the chatter

        result = True
        for line in self:
            cleaned_vals = line.move_id._cleanup_write_orm_values(line, vals)
            if not cleaned_vals:
                continue

            # Auto-fill amount_currency if working in single-currency.
            if 'currency_id' not in cleaned_vals \
                and line.currency_id == line.company_currency_id \
                and any(field_name in cleaned_vals for field_name in ('debit', 'credit')):
                cleaned_vals.update({
                    'amount_currency': vals.get('debit', 0.0) - vals.get('credit', 0.0),
                })
            

            result |= super(YDSAccountMoveLine, line).write(cleaned_vals)

            if not line.move_id.is_invoice(include_receipts=True):
                continue

            # Ensure consistency between accounting & business fields.
            # As we can't express such synchronization as computed fields without cycling, we need to do it both
            # in onchange and in create/write. So, if something changed in accounting [resp. business] fields,
            # business [resp. accounting] fields are recomputed.
            if any(field in cleaned_vals for field in ACCOUNTING_FIELDS):
                price_subtotal = line._get_price_total_and_subtotal().get('price_subtotal', 0.0)
                to_write = line._get_fields_onchange_balance(price_subtotal=price_subtotal)
                print("1st")
                print(to_write)
                to_write.update(line._get_price_total_and_subtotal(
                    price_unit=to_write.get('price_unit', line.price_unit),
                    quantity=to_write.get('quantity', line.quantity),
                    discount=to_write.get('discount', line.discount),
                ))
                print("2nd")
                print(to_write)
                result |= super(YDSAccountMoveLine, line).write(to_write)
            elif any(field in cleaned_vals for field in BUSINESS_FIELDS):
                to_write = line._get_price_total_and_subtotal()
                print("3rd")
                print(to_write)
                to_write.update(line._get_fields_onchange_subtotal(
                    price_subtotal=to_write['price_subtotal'],
                ))
                print("4th")
                print(to_write)
                result |= super(YDSAccountMoveLine, line).write(to_write)
       
        # Check total_debit == total_credit in the related moves.
        if self._context.get('check_move_validity', True):
           self.mapped('move_id')._check_balanced()
       


        self.mapped('move_id')._synchronize_business_models({'line_ids'})

        return result


   

    @api.onchange('discount')
    def recalcTax(self):
        for line in self:
           line.move_id._recompute_tax_lines()

