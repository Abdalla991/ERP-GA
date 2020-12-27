from odoo import models, fields, api, exceptions
from odoo.exceptions import UserError, ValidationError



class YDSResPartner(models.Model):
    _inherit = "res.partner"
    
    yds_customer_universal_discount_rate = fields.Float('Universal Discount', default="0.0",readonly=False)

    


    