from odoo import models, fields, api, exceptions
from odoo.exceptions import UserError, ValidationError
import ipdb #Remove before publishing

#account.move -- account.move.line -- account.analytic.line

class YDSAccountMove(models.Model):
    _inherit = "account.move"
    yds_total_discount = fields.Float(string='Total Discount',readonly=True,store=True)
    yds_pricelist_account_id = fields.Integer(string='Pricelist account ID',  readonly=True,store=True)
    yds_pricelist_name = fields.Char(string ='Pricelist Name',readonly=True,store=True)

    yds_amount_untaxed = fields.Monetary(string='Untaxed Amount', store=True, readonly=True, currency_field='company_currency_id')
    yds_amount_untaxed_after_discount = fields.Monetary(string='Untaxed Amount After Discount', store=True, readonly=True, currency_field='company_currency_id')
    yds_is_sales_order = fields.Boolean(string="is Sales Order")

    #pricelist_related_fields
    
    

    #added because of the change in pricelist subtotal
    yds_amount_total = fields.Monetary(string='Total', store=True, readonly=True, compute='_compute_amount2')

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
        'line_ids.price_subtotal',   #change to moataz's new variable
        'yds_total_discount',
        'pricelist_id')
    def _compute_amount(self):
        super(YDSAccountMove, self)._compute_amount()
        
        for rec in self:
            
            rec.yds_total_discount=0
            rec._calculatePricelistDiscount()
            rec.amount_total = rec.amount_tax + rec.amount_untaxed - rec.yds_total_discount
            # rec.update_pricelist_account()
            #depending on the change of the price_subtotal field
            rec.yds_amount_untaxed = rec.amount_untaxed
            rec.yds_amount_untaxed_after_discount = rec.yds_amount_untaxed - rec.yds_total_discount
           
    #to avoid ignoring of discount lines due to dubplicate line names
    @api.onchange('invoice_line_ids')
    def rename_line(self):
        print("rename_lines")
        productNames = [] 
        productCounts = [] 
        for rec in self :
            innerloopCount=0
            for line in rec.invoice_line_ids:
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

    @api.onchange('invoice_line_ids')
    def readjust_lines(self):
        print("----------------------------------")
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
                    



    @api.depends('amount_total')
    def _compute_amount2(self):
        for rec in self:
            rec.yds_amount_total = rec.yds_amount_total

    def _calculatePricelistDiscount(self):
        for rec in self:
            for line in rec.line_ids:
                rec.yds_total_discount += line.price_unit * ( (line.discount or 0.0) / 100.0) * line.quantity
            
            rec.remove_lines_disc() #somehow wont work after .add_lines()
            rec.add_lines()
    
    @api.model
    def _prepare_refund(self, invoice, date_invoice=None, date=None, description=None, journal_id=None):
        yds_res = super(YDSAccountMove, self)._prepare_refund(invoice, date_invoice=None, date=None,
                                                                      description=None, journal_id=None)
        yds_res['yds_total_discount'] = self.yds_total_discount
        return yds_res

    def add_lines(self):       
        # OVERRIDE
        # Don't change anything on moves used to cancel another ones.
        # return super()._post(soft=False)
        print("add_lines called")
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
                    if already_exists:
                        print("Aleady exisits 1 "+line.name)
                        exists=True
                        amount = pricelist_discount_line_amount
                        if product_discount_account \
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
                        total_balance = sum(other_lines.mapped('balance'))
                        total_amount_currency = sum(other_lines.mapped('amount_currency'))
                        terms_lines.update({
                            'amount_currency': -total_amount_currency,
                            'debit': total_balance < 0.0 and -total_balance or 0.0,
                            'credit': total_balance > 0.0 and total_balance or 0.0,
                        })
                    if not already_exists and pricelist_discount_line_amount > 0:
                        print("does not exist")
                        search_ids =  self.env['account.move.line'].search([],order="id desc")
                        last_id = search_ids and max(search_ids)
                        predictedId = last_id.id + 1

                        in_draft_mode = self != self._origin
                        # not in_draft_mode and 
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
                                            # duplicate_id = self.invoice_line_ids.filtered(
                                            #     lambda line: line.name and line.name.find(lineName) == 0)
                                            # self.invoice_line_ids = self.invoice_line_ids - duplicate_id
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
                                    total_amount_currency = sum(other_lines.mapped('amount_currency'))
                                    print("exists? " + str(exists))
                                    # if(exists):
                                    #     total_balance = sum(other_lines.mapped('balance'))
                                    # else:
                                    #     total_balance = sum(other_lines.mapped('balance')) + amount
                                    print("total balance: "+ str(total_balance))
                                    terms_lines.update({
                                        'amount_currency': -total_amount_currency,
                                        'debit': total_balance < 0.0 and -total_balance or 0.0,
                                        'credit': total_balance > 0.0 and total_balance or 0.0,
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
                                    print(self)
                                    # ipdb.set_trace()
                                    self.line_ids = [(1, already_exists.id, dict1), (1, terms_lines.id, dict2)] 
                                    print()
                        print("in draft mode 3")

                    # Add discount line.
      
            # Post entries.
            # return super()._post(soft=False)
    def remove_lines_disc(self):
        print("checking lines to remove")
        for move in self:
            for line in move.invoice_line_ids:
                if line.discount == 0:
                    lineName = line.name[:64]+" discount "
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

    # def unlink(self):
    #     print("unlink called")
    #     for line in self:
    #         lineName = line.name[:64]+" discount " + str(line.sequence)
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
            
    #     res = super(YDSAccountMoveLine, self).unlink()
    #     return res


# class YDSAccountAnalyticLine(models.Model):
#     _inherit = 'account.analytic.line'
#     yds_product_discount = fields.Float(string='Total Product Discounts', store=True, readonly=True)



