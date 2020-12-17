from odoo import models, fields, api, exceptions, _
from odoo.exceptions import UserError, ValidationError
import ipdb #Remove before publishing

#this file is concerned with the addition/removal of new lines

class YDSAccountMove(models.Model):
    _inherit = "account.move"

    #Rename lines with an already existing product to avoid ignoring of discount lines due to duplicate line names
    @api.onchange('invoice_line_ids')
    def rename_lines(self):
        productNames = [] 
        productCounts = []
        for rec in self :
            innerloopCount=0
            for line in rec.invoice_line_ids:
                innerloopCount+=1
                if line.product_id.name in productNames:
                    index = productNames.index(line.product_id.name)
                    productCounts[index]+=1
                    line.name = line.product_id.name +" ("+str(productCounts[index])+")"
                else:   
                    productNames.append(line.product_id.name)
                    productCounts.append(1)

    #On row deletion or addition readd lines
    #FIX
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
                    # if line.product_id.type != 'product' or line.product_id.valuation != 'real_time':
                    #     continue

                    sale_uni_discount_account = move.ks_sales_discount_account_id
                    purchase_uni_discount_account = move.ks_purchase_discount_account_id
                    # unversal_discount_account = accounts['expense'] or self.journal_id.default_account_id
                    # if not sale_uni_discount_account or not purchase_uni_discount_account:
                    #     continue

                    sign = -1 if move.move_type == 'out_refund' else 1

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
                    already_exists = move.line_ids.filtered(
                        lambda line: line.name and line.name.find(lineName) == 0)
                    terms_lines = move.line_ids.filtered(
                        lambda line: line.account_id.user_type_id.type in ('receivable', 'payable'))
                    other_lines = move.line_ids.filtered(
                        lambda line: line.account_id.user_type_id.type not in ('receivable', 'payable'))
                    if already_exists:
                        print("Uni Aleady exisits 1 "+line.name)
                        exists=True
                        amount = universal_discount_line_amount
                        print("new amount = "+str(amount))
                        if sale_uni_discount_account \
                                and (move.move_type == "out_invoice"
                                    or move.move_type == "out_refund")\
                                and amount > 0:
                            if move.move_type == "out_invoice":
                                already_exists.update({
                                    'debit': amount > 0.0 and amount or 0.0,
                                    'credit': amount < 0.0 and -amount or 0.0,
                                    'amount_currency': amount,
                                })
                            else:
                                already_exists.update({
                                    'debit': amount < 0.0 and -amount or 0.0,
                                    'credit': amount > 0.0 and amount or 0.0,
                                    'amount_currency': -amount,
                                })
                        if purchase_uni_discount_account \
                                and (move.move_type == "in_invoice"
                                        or move.move_type == "in_refund")\
                                and amount > 0:
                            if move.move_type == "in_invoice":
                                already_exists.update({
                                    'debit': amount < 0.0 and -amount or 0.0,
                                    'credit': amount > 0.0 and amount or 0.0,
                                    'amount_currency': amount,
                                })
                            else:
                                already_exists.update({
                                    'debit': amount > 0.0 and amount or 0.0,
                                    'credit': amount < 0.0 and -amount or 0.0,
                                    'amount_currency': -amount,
                                })
                        already_exists.update({
                                'analytic_account_id': line.analytic_account_id.id,
                            })
                        move._recompute_dynamic_lines(recompute_all_taxes=True, recompute_tax_base_amount=True)
                    if not already_exists and hasDiscount:
                        print("Uni does not exist 1")
                        in_draft_mode = move != move._origin
                        # not in_draft_mode and 
                        if move.move_type == 'out_invoice':
                            if hasDiscount and move.move_type in type_list:
                                in_draft_mode = move != move._origin
                                terms_lines = move.line_ids.filtered(
                                    lambda line: line.account_id.user_type_id.type in ('receivable', 'payable'))
                                already_exists = move.line_ids.filtered( lambda line: line.name and line.name.find(lineName) == 0)
                                create_method = in_draft_mode and \
                                                move.env['account.move.line'].new or\
                                                move.env['account.move.line'].create
                                if sale_uni_discount_account \
                                        and (move.move_type == "out_invoice"
                                            or move.move_type == "out_refund"):
                                    amount = universal_discount_line_amount
                                    dict = {
                                        'move_name': move.name,
                                        'name':lineName,
                                        'move_id': move._origin,
                                        'yds_parent_id' :line.id,
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
                                        'amount_currency': amount,
                                        })
                                    else:
                                        dict.update({
                                            'debit': amount < 0.0 and -amount or 0.0,
                                            'credit': amount > 0.0 and amount or 0.0,
                                            'amount_currency': -amount,
                                        })
                                    if in_draft_mode:
                                        # print("in Uni draft mode 1 sale")
                                        duplicate_id = move.line_ids.filtered(
                                            lambda line: line.name and line.name.find(lineName) == 0)
                                        move.line_ids = move.line_ids - duplicate_id
                                        move.line_ids += create_method(dict)
                                        move._recompute_dynamic_lines(recompute_all_taxes=True, recompute_tax_base_amount=True)
                                        # Updation of Invoice Line Id
                                    else:
                                        dict.update({
                                        'price_unit': 0.0,
                                        'debit': 0.0,
                                        'credit': 0.0,
                                            })
                                        move.line_ids = [(0, 0, dict)]

                                if purchase_uni_discount_account\
                                        and (move.move_type == "in_invoice"
                                            or move.move_type == "in_refund"):
                                    amount = universal_discount_line_amount
                                    dict = {
                                        'move_name': move.name,
                                        'name':lineName,
                                        'move_id': move._origin,
                                        'yds_parent_id' :line.id,
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

                                    if move.move_type == "in_invoice":
                                        dict.update({
                                            'debit': amount < 0.0 and -amount or 0.0,
                                            'credit': amount > 0.0 and amount or 0.0,
                                            'amount_currency': -amount,
                                        })
                                    else:
                                        dict.update({
                                            'debit': amount > 0.0 and amount or 0.0,
                                            'credit': amount < 0.0 and -amount or 0.0,
                                            'amount_currency': amount,
                                        })
                                        duplicate_id = move.line_ids.filtered(
                                            lambda line: line.name and line.name.find(lineName) == 0)
                                        move.line_ids = move.line_ids - duplicate_id
                                        move.line_ids += create_method(dict)
                                        move._recompute_dynamic_lines(recompute_all_taxes=True, recompute_tax_base_amount=True)
                                        # Updation of Invoice Line Id
                                if in_draft_mode:
                                    # print("Uni in draft mode 2")
                                    # Update the payement account amount
                                    move._recompute_dynamic_lines(recompute_all_taxes=True, recompute_tax_base_amount=True)
                                else: 
                                    # print("Uni not in draft mode final")
                                    already_exists = self.line_ids.filtered(
                                            lambda line: line.name and line.name.find(lineName) == 0)
                                    already_exists.with_context(check_move_validity=False).update({
                                        'debit': amount > 0.0 and amount or 0.0, 
                                        'credit': amount < 0.0 and -amount or 0.0,
                                        'amount_currency': amount,
                                        })
                                    # ipdb.set_trace()
                                    move.with_context(check_move_validity=False)._recompute_dynamic_lines(recompute_all_taxes=True, recompute_tax_base_amount=True)
                                    print()


  
    #Remove Universal discount lines if rate == 0
    @api.onchange('ks_global_discount_rate')
    def remove_lines_uni(self):
        print("checking Uni lines to remove")
        for move in self:
            for line in move.invoice_line_ids:
                if line.name and move.ks_global_discount_rate == 0:
                    lineName = line.name[:64]+" Universal discount "
                    already_exists = move.line_ids.filtered(
                                lambda line: line.name and line.name.find(lineName) == 0)
                    if already_exists:
                        print("found and removing: "+already_exists.name)
                        # ipdb.set_trace()
                        print(move.line_ids)
                        move.line_ids -= already_exists
                        print(move.line_ids)
                        print("Removed!!!! "+already_exists.name)
                        # terms_lines.update({
                        #     'amount_currency': -total_amount_currency,
                        #     'debit': total_balance < 0.0 and -total_balance or 0.0,
                        #     'credit': total_balance > 0.0 and total_balance or 0.0,
                        #     # 'price_unit': total_balance,
                        # })
                        move._recompute_dynamic_lines(recompute_all_taxes=True, recompute_tax_base_amount=True)

                        
         
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
                    # Filter out lines being not eligible for discount line.
                    # if line.product_id.type != 'product' or line.product_id.valuation != 'real_time':
                    #     continue

                    product_discount_account = move.pricelist_id.yds_assigned_discount_account.id
                    if not product_discount_account: 
                        continue

                    sign = -1 if move.move_type == 'out_refund' else 1
                    #Calculations
                    amount = ((line.credit or 0.0) - (line.debit or 0.0))*sign
                    pricelist_discount_line_amount =(line.price_unit * ( (line.discount or 0.0) / 100.0) *line.quantity)
                    hasDiscount = pricelist_discount_line_amount > 0  

                    lineName = line.name[:64]+" discount "
                    print("------Existing Lines ------")
                    for l in move.line_ids:
                        print(str(l.name))   
                    print("---------------------------")

                    print("expected name: "+ lineName)

                    already_exists = move.line_ids.filtered(
                        lambda line: line.name and line.name.find(lineName) == 0)
                    terms_lines = move.line_ids.filtered(
                        lambda line: line.account_id.user_type_id.type in ('receivable', 'payable'))
                    other_lines = move.line_ids.filtered(
                        lambda line: line.account_id.user_type_id.type not in ('receivable', 'payable'))
                    if pricelist_discount_line_amount > 0 :
                        if already_exists:
                            print("Aleady exisits  "+line.name)
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
                                        'amount_currency': amount,
                                    })
                                else:
                                    already_exists.update({
                                        'debit': amount < 0.0 and -amount or 0.0,
                                        'credit': amount > 0.0 and amount or 0.0,
                                        'amount_currency': -amount,
                                    })
                                already_exists.update({
                                    'analytic_account_id': line.analytic_account_id.id,
                                })
                            move._recompute_dynamic_lines(recompute_all_taxes=True, recompute_tax_base_amount=True)
                        if not already_exists and hasDiscount:
                            print("does not exist")
                            in_draft_mode = move != move._origin
                            if move.move_type == 'out_invoice':
                                newLineName = line.name[:64]+" discount "
                                if hasDiscount and move.move_type in type_list:
                                    in_draft_mode = move != move._origin
                                    terms_lines = move.line_ids.filtered(
                                        lambda line: line.account_id.user_type_id.type in ('receivable', 'payable'))
                                    already_exists = move.line_ids.filtered( lambda line: line.name and line.name.find(newLineName) == 0)
                                    create_method = in_draft_mode and \
                                                    move.env['account.move.line'].new or\
                                                    move.env['account.move.line'].create

                                    if product_discount_account \
                                            and (move.move_type == "out_invoice"
                                                or move.move_type == "out_refund"):
                                        amount = pricelist_discount_line_amount
                                        print("-----------------------------------------------------")
                                        print(str(line.id))
                                        dict = {
                                            'move_name': move.name,
                                            'name':newLineName,
                                            'move_id': move._origin,
                                            'product_id': line.product_id.id,
                                            'yds_parent_id' :line.id,
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
                                            'amount_currency': pricelist_discount_line_amount,
                                            })
                                        else:
                                            dict.update({
                                                'debit': pricelist_discount_line_amount < 0.0 and -pricelist_discount_line_amount or 0.0,
                                                'credit': pricelist_discount_line_amount > 0.0 and pricelist_discount_line_amount or 0.0,
                                                'amount_currency': -pricelist_discount_line_amount,
                                                
                                            })
                                        if in_draft_mode:
                                            print("in draft mode 1")
                                            #revice duplicate
                                            duplicate_id = move.line_ids.filtered(
                                                lambda line: line.name and line.name.find(newLineName) == 0)
                                            move.line_ids = move.line_ids - duplicate_id
                                            move.line_ids += create_method(dict)
                                            # Updation of Invoice Line Id
                                            move._recompute_dynamic_lines(recompute_all_taxes=True, recompute_tax_base_amount=True)
                                        else:
                                            print("not in draft mode 1")
                                            duplicate_id = move.line_ids.filtered(
                                                lambda line: line.name and line.name.find(newLineName) == 0)
                                            move.line_ids = move.line_ids - duplicate_id
                                            dict.update({
                                            'price_unit':0,
                                            'debit': 0 , 
                                            'credit': 0,
                                            })
                                            move.line_ids = [(0, 0, dict)]
                                    if in_draft_mode:
                                        print("in draft mode 2")
                                        # Update the payement account amount
                                        move._recompute_dynamic_lines(recompute_all_taxes=True, recompute_tax_base_amount=True)
                                    else: 
                                        print("not in draft mode 2")
                                        already_exists = move.line_ids.filtered(
                                                lambda line: line.name and line.name.find(newLineName) == 0)
                                        already_exists.with_context(check_move_validity=False).update({
                                                'debit': amount > 0.0 and amount or 0.0, 
                                                'credit': amount < 0.0 and -amount or 0.0,
                                                'amount_currency': pricelist_discount_line_amount,
                                                })
                                        move.with_context(check_move_validity=False)._recompute_dynamic_lines(recompute_all_taxes=True, recompute_tax_base_amount=True)
                                        # ipdb.set_trace()



    #Remove regular discount line per product when discount == 0
    @api.onchange('invoice_line_ids')
    def remove_lines_disc(self):
        print("checking lines to remove")
        for move in self:
            for line in move.invoice_line_ids:
                if line.name and line.discount == 0:
                    lineName = line.name[:64]+" discount "
                    already_exists = move.line_ids.filtered(
                                lambda line: line.name and line.name.find(lineName) == 0)
                    if already_exists:
                        print("found and removing: "+already_exists.name)
                        # ipdb.set_trace()
                        print(move.line_ids)
                        move.line_ids -= already_exists
                        print(move.line_ids)
                        print("Removed!!!! "+already_exists.name)
                        # terms_lines.update({
                        #     'amount_currency': -total_amount_currency,
                        #     'debit': total_balance < 0.0 and -total_balance or 0.0,
                        #     'credit': total_balance > 0.0 and total_balance or 0.0,
                        #     # 'price_unit': total_balance,
                        # })
                        move._recompute_dynamic_lines(recompute_all_taxes=True, recompute_tax_base_amount=True)

                        # self.line_ids = [(1, already_exists.id, dict1), (1, terms_lines.id, dict2)] 

    #remove lines when invoice line row is removed
    @api.onchange('invoice_line_ids')
    def remove_cached_lines(self):
        print("Checking lines to remove")
        for move in self:

            lines_to_be_saved_names = []
            lines_to_be_removed = move.line_ids

            #remove all non discount / Uni discount lines from the list
            for line in move.line_ids:
                if not "discount" in str(line.name):
                    lines_to_be_removed-= line

            #debugging purposes REMOVE ME
            print("before cleaning")
            for l in lines_to_be_removed:
                print (l.name)
            
            #remove existing invoice lines from the list 
            for invoice_line in move.invoice_line_ids:
                if invoice_line.discount > 0 :
                    for l in lines_to_be_removed:
                        if l.name == invoice_line.name + " discount ":
                            lines_to_be_removed -= l
                if move.ks_global_discount_rate > 0:
                    for l in lines_to_be_removed:
                        if l.name == invoice_line.name + " Universal discount ":
                            lines_to_be_removed -= l

            #debugging purposes REMOVE ME
            print("after cleaning")
            for l in lines_to_be_removed:
                print (l.name)

            #remove lines that have been removed
            move.line_ids -= lines_to_be_removed
            #rebalance
            move._recompute_dynamic_lines(recompute_all_taxes=True, recompute_tax_base_amount=True)
          