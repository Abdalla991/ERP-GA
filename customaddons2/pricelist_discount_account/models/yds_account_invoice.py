# from odoo import api, fields, models
# from odoo.exceptions import UserError, ValidationError

# class YdsPricelistDiscountInvoice(models.Model):
#     _inherit = "account.move"
#     yds_amount_discount = fields.Monetary(string='Pricelist Discount',
#                                          readonly=True,
#                                          compute='_compute_amount',
#                                          store=True, track_visibility='always')
#      yds_enable_discount_account=fields.Boolean(compute='yds_verify_pricelist_account')
#      yds_pricelist_discount_account= fields.Integer(compute='yds_verify_pricelist_account')                  
    
    
#     @api.depends('company_id.yds_enable_discount_account')
#     def yds_verify_pricelist_account(self):
#         for rec in self:
#             rec.yds_enable_discount_account = rec.company_id.yds_enable_discount_account
#             rec.yds_pricelist_discount_account_id = rec.company_id.yds_pricelist_discount_account.id

    
