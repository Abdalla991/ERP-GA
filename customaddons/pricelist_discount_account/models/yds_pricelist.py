from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError

class YDSPricelist(models.Model):
    _inherit = "product.pricelist"
    yds_assigned_discount_account = fields.Many2one('account.account', string="Pricelist Discount Account", readonly=False)

