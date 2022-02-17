from odoo import models, fields, api, exceptions, _
from odoo.exceptions import UserError, ValidationError

#account.move -- account.move.line -- account.analytic.line

class YDSAccountMove(models.Model):
    _inherit = "account.move"

    #KS variables (Universal Discount)
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

    # YDS regular discount related variables
    #########################################################################
    yds_total_discount = fields.Float(string='Total Discount',readonly=True,store=True)
    yds_pricelist_account_id = fields.Integer(string='Pricelist account ID',  readonly=True,store=True)
    yds_pricelist_name = fields.Char(string ='Pricelist Name',readonly=True,store=True)
    yds_amount_untaxed = fields.Monetary(string='Untaxed Amount', store=True, readonly=True)
    yds_amount_untaxed_after_discount = fields.Monetary(string='Untaxed Amount After Discount', store=True, readonly=True)
    yds_amount_untaxed_after_all_discounts = fields.Monetary(string='Untaxed Amount After Discount', compute='_compute_untaxed_after_all_discounts',store=True, readonly=True)
    yds_is_sales_order = fields.Boolean(string="is Sales Order")
    yds_amount_tax = fields.Monetary(string='Tax', store=True, readonly=True)

    @api.depends(
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
        'line_ids.analytic_account_id',
        'yds_total_discount',
        'ks_global_discount_rate',
        'pricelist_id',
        'partner_id')
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

            for line in move.line_ids:
                if line.currency_id and line in move._get_lines_onchange_currency():
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
            move.amount_untaxed = sign * (total_untaxed_currency if len(currencies) == 1 else total_untaxed)
            move.amount_tax = sign * (total_tax_currency if len(currencies) == 1 else total_tax)
            move.amount_untaxed_signed = -total_untaxed
            move.amount_tax_signed = -total_tax

            move.yds_total_discount=0
            move._calculatePricelistDiscount()
            move.yds_amount_untaxed = sign * (total_untaxed_currency if len(currencies) == 1 else total_untaxed)
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

            if (move.move_type == 'out_invoice'):
                move.amount_total_signed = abs(total) if move.move_type == 'entry' else -total- move.yds_total_discount - move.ks_amount_discount
            else:
                move.amount_total_signed = abs(total) if move.move_type == 'entry' else -(total- (move.yds_total_discount + move.ks_amount_discount))

            move.amount_residual_signed = total_residual
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
            #call add lines once when coming from a sale order
            if(move.yds_is_sales_order):
                move.add_all_lines()
                move.yds_is_sales_order=False

    @api.depends(
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
        'line_ids.analytic_account_id',
        'yds_total_discount',
        'ks_global_discount_rate',
        'pricelist_id',
        'partner_id')
    def _compute_untaxed_after_all_discounts(self):
        for move in self:
            move.yds_amount_untaxed_after_all_discounts = move.yds_amount_untaxed_after_discount - move.ks_amount_discount
    
    @api.onchange('pricelist_id')
    def change_currency(self):
        if self.pricelist_id:
            self.currency_id=self.pricelist_id.currency_id

    @api.onchange('invoice_line_ids',
                    'ks_global_discount_rate',
                    'pricelist_id')
    def add_all_lines(self):
        for move in self:
            # move.rename_lines()   
            print("Calling add lines") 
            #Ensure no discount lines are added unless move_type is an invoice
            if move.move_type in ['out_invoice', 'out_refund']:
                move.add_lines_uni()
                move.add_lines()
                move._recompute_tax_lines()

    @api.onchange('ks_global_discount_rate')
    def recalc_tax(self):
        print("recalc_tax called")
        for move in self:
            move._recompute_tax_lines()

    #Calculate yds_total_discount
    def _calculatePricelistDiscount(self):
        for rec in self:
            for line in rec.line_ids:
                rec.yds_total_discount += line.price_unit * ( (line.discount or 0.0) / 100.0) * line.quantity
            
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
        for record in self:
            if record.ks_global_discount_type == "percent":
                if record.ks_global_discount_rate > 100 or record.ks_global_discount_rate < 0:
                    raise ValidationError('You cannot enter percentage value greater than 100.')
            else:
                if record.ks_global_discount_rate < 0 or record.amount_untaxed < 0:
                    raise ValidationError(
                        'You cannot enter discount amount greater than actual cost or value lower than 0.')
       
    #TEST THIS FUNCTION
    @api.model
    def _prepare_refund(self, invoice, date_invoice=None, date=None, description=None, journal_id=None):
        ks_res = super(YDSAccountMove, self)._prepare_refund(invoice, date_invoice=None, date=None,
                                                                      description=None, journal_id=None)
        ks_res['ks_global_discount_rate'] = self.ks_global_discount_rate
        ks_res['ks_global_discount_type'] = self.ks_global_discount_type
        return ks_res
       
    #TEST THIS FUNCTION 
    @api.model
    def _prepare_refund(self, invoice, date_invoice=None, date=None, description=None, journal_id=None):
        yds_res = super(YDSAccountMove, self)._prepare_refund(invoice, date_invoice=None, date=None,
                                                                      description=None, journal_id=None)
        yds_res['yds_total_discount'] = self.yds_total_discount
        return yds_res


    # def _check_balanced(self):
    #     ''' Assert the move is fully balanced debit = credit.
    #     An error is raised if it's not the case.
    #     '''      
    #     moves = self.filtered(lambda move: move.line_ids)
    #     if not moves:
    #         return
    #     for move in self:
    #         print ("---------Start _check_balanced---------")
    #         for line in move.line_ids:
    #             print ("Line Name: "+str(line.name))
    #             print("credit: "+str(line.credit)+" - "+"debit: "+ str(line.debit)+" - "+"balance: "+ str(line.balance)+" - "+"amount_currency: "+ str(line.amount_currency))
    #         print ("---------End _check_balanced---------")



    #Had to override this function to add universal discount to tax calculations

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

            balance_taxes_res = base_line.tax_ids._origin.with_context(force_sign=move._get_tax_force_sign()).compute_all(
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
                repartition_tags = base_line.tax_ids.flatten_taxes_hierarchy().mapped(repartition_field).filtered(lambda x: x.repartition_type == 'base').tag_ids
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
            line.tax_tag_ids = compute_all_vals['base_tags'] or [(5, 0, 0)]

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
                taxes_map_entry['tax_base_amount'] += self._get_base_amount_to_display(tax_vals['base'], tax_repartition_line, tax_vals['group'])
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

    #Override to change cost/stock value line names
    def _stock_account_prepare_anglo_saxon_out_lines_vals(self):
        lines_vals_list = []
        for move in self:
            if not move.is_sale_document(include_receipts=True) or not move.company_id.anglo_saxon_accounting:
                continue

            for line in move.invoice_line_ids:

                # Filter out lines being not eligible for COGS.
                if line.product_id.type != 'product' or line.product_id.valuation != 'real_time':
                    continue

                # Retrieve accounts needed to generate the COGS.
                accounts = (
                    line.product_id.product_tmpl_id
                    .with_company(line.company_id)
                    .get_product_accounts(fiscal_pos=move.fiscal_position_id)
                )
                debit_interim_account = accounts['stock_output']
                credit_expense_account = accounts['expense'] or self.journal_id.default_account_id
                if not debit_interim_account or not credit_expense_account:
                    continue

                # Compute accounting fields.
                sign = -1 if move.move_type == 'out_refund' else 1
                price_unit = line._stock_account_get_anglo_saxon_price_unit()
                balance = sign * line.quantity * price_unit

                # Add interim account line.
                lines_vals_list.append({
                    'name': line.name[:64]+ " Stock Value",
                    'move_id': move.id,
                    'product_id': line.product_id.id,
                    'product_uom_id': line.product_uom_id.id,
                    'quantity': line.quantity,
                    'price_unit': price_unit,
                    'debit': balance < 0.0 and -balance or 0.0,
                    'credit': balance > 0.0 and balance or 0.0,
                    'account_id': debit_interim_account.id,
                    'exclude_from_invoice_tab': True,
                    'is_anglo_saxon_line': True,
                })

                # Add expense account line.
                lines_vals_list.append({
                    'name': line.name[:64] +" Cost",
                    'move_id': move.id,
                    'product_id': line.product_id.id,
                    'product_uom_id': line.product_uom_id.id,
                    'quantity': line.quantity,
                    'price_unit': -price_unit,
                    'debit': balance > 0.0 and balance or 0.0,
                    'credit': balance < 0.0 and -balance or 0.0,
                    'account_id': credit_expense_account.id,
                    'analytic_account_id': line.analytic_account_id.id,
                    'analytic_tag_ids': [(6, 0, line.analytic_tag_ids.ids)],
                    'exclude_from_invoice_tab': True,
                    'is_anglo_saxon_line': True,
                })
        return lines_vals_list

    def action_switch_invoice_into_refund_credit_note(self):
        if any(move.move_type not in ('in_invoice', 'out_invoice') for move in self):
            raise ValidationError(_("This action isn't available for this document."))

        for move in self:
            reversed_move = move._reverse_move_vals({}, False)
            new_invoice_line_ids = []
            for cmd, virtualid, line_vals in reversed_move['line_ids']:
                if not line_vals['exclude_from_invoice_tab']:
                    new_invoice_line_ids.append((0, 0,line_vals))
            if move.amount_total < 0:
                # Inverse all invoice_line_ids
                for cmd, virtualid, line_vals in new_invoice_line_ids:
                    line_vals.update({
                        'quantity' : -line_vals['quantity'],
                        'amount_currency' : -line_vals['amount_currency'],
                        'debit' : line_vals['credit'],
                        'credit' : line_vals['debit']
                    })
           
            move.write({
                'move_type': move.move_type.replace('invoice', 'refund'),
                'invoice_line_ids' : [(5, 0, 0)],
                'partner_bank_id': False,
            })
            move.write({'invoice_line_ids' : new_invoice_line_ids})
            # import ipdb
            # ipdb.set_trace()
            move.add_all_lines()


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
        subtotal = quantity * price_unit
        
        yds_subtotal = quantity * line_discount_price_unit

        # Compute 'price_total'.
        if taxes:
            #Use price_unit instead of Odoo's DEFAULT line_discount_price_unit to calc tax without discount
            #To seperate discount from net sales
            taxes_res = taxes._origin.compute_all(price_unit,
                quantity=quantity, currency=currency, product=product, partner=partner, is_refund=move_type in ('out_refund', 'in_refund'))
            
            res['price_subtotal'] = taxes_res['total_excluded']
            res['price_total'] = taxes_res['total_included']

            #YDS Specific fields to store all values (INCASE we need them in the future)
            yds_taxes_res = taxes._origin.compute_all(price_unit,
                quantity=quantity, currency=currency, product=product, partner=partner, is_refund=move_type in ('out_refund', 'in_refund'))
            res['yds_price_subtotal'] = yds_taxes_res['total_excluded'] 
            res['yds_price_total'] = yds_taxes_res['total_included']
        else:
            res['price_total'] = res['price_subtotal'] = subtotal
            res['yds_price_total'] = res['yds_price_subtotal'] = yds_subtotal
        #In case of multi currency, round before it's use for computing debit credit
        if currency:
            res = {k: currency.round(v) for k, v in res.items()}
        return res
 
    #Recalc tax if line discount value has changed
    @api.onchange('discount')
    def recalcTax(self):
       for line in self:
            if not line.tax_repartition_line_id:
                line.recompute_tax_line = True

