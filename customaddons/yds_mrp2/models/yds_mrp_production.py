from odoo import models, fields, api, exceptions,_
from odoo.exceptions import ValidationError
from collections import defaultdict
import ipdb 
from datetime import datetime

class YdsMrpProduction(models.Model):
    _inherit = "mrp.production"
    yds_bom_expired = fields.Boolean(string="Selected Bill of Material has expired !", readonly=True, Default="False")

    @api.depends('product_id', 'bom_id', 'company_id')
    def _compute_allowed_product_ids(self):
    
        for production in self: 
            if production.bom_id:
                if production.bom_id.yds_start_date and production.bom_id.yds_end_date:
                    start = datetime.strptime(str(production.bom_id.yds_start_date), '%Y-%m-%d')
                    end = datetime.strptime(str(production.bom_id.yds_end_date), '%Y-%m-%d')
                    current = datetime.strptime(str(datetime.now().date()), '%Y-%m-%d')
                    if start <= current and end > current :
                        production.yds_bom_expired = False
                        print(str(production.yds_bom_expired))
                    else:
                        production.yds_bom_expired = True
                        print(str(production.yds_bom_expired))

        return super(YdsMrpProduction, self)._compute_allowed_product_ids()
