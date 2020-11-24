from odoo import models, fields, api, exceptions
from datetime import datetime

class YdsMrpBom(models.Model):
    _inherit = "mrp.bom"
    start_date = fields.Date(string="Start Date")
    end_date = fields.Date(string="End Date")


    @api.onchange('bom_line_ids','product_tmpl_id', 'product_qty','product_uom_id')
    def _update_bom_line_custom_fields(self):
        for bom in self:
            for bom_line in bom.bom_line_ids:
                bom_line.yds_record_product_uom_id = bom.product_uom_id
                bom_line.yds_record_product_qty = bom.product_qty



class YdsMrpBomLine(models.Model):
    _inherit = "mrp.bom.line"


    yds_product_percent = fields.Float(string='Percentage',store=True , default=0.0)
    yds_product_qty = fields.Float('Quantity', default=1.0, digits='Product Unit of Measure', required=True)

    yds_record_product_uom_id = fields.Integer('Product Unit of Measure')
    yds_record_product_qty = fields.Float('Quantity', default=1.0, digits='Product Unit of Measure', required=True)

    yds_product_uom_id = fields.Integer('Product Unit of Measure2')


    @api.onchange('yds_product_percent', 'product_uom_id', 'yds_record_product_uom_id', 'yds_record_product_qty')
    def _yds_compute_qty(self):
        for bom_line in self:
            bom_line.yds_product_uom_id = bom_line.product_uom_id
            if bom_line.yds_product_percent != 0.0:
                if bom_line.yds_product_uom_id == bom_line.yds_record_product_uom_id:
                    bom_line.yds_product_qty = bom_line.yds_product_percent / 100 * bom_line.yds_record_product_qty
                    bom_line.product_qty = bom_line.yds_product_qty

            
                



class YdsMrpProduction(models.Model):
    _inherit = "mrp.production"
    yds_bom_expired = fields.Boolean(string="Selected Bill of Material has expired", Default="False")
    
    @api.depends('product_id', 'bom_id', 'company_id')
    def _compute_allowed_product_ids(self):
    
        for production in self: 
            if production.bom_id:
                start = datetime.strptime(str(production.bom_id.start_date), '%Y-%m-%d')
                end = datetime.strptime(str(production.bom_id.end_date), '%Y-%m-%d')
                current = datetime.strptime(str(datetime.now().date()), '%Y-%m-%d')
                if start < current and end > current :
                    production.yds_bom_expired = True
                    # if  start < current:
                    #     production.yds_bom_expired.string="ab"
                    # elif end > current 
                    #     production.yds_bom_expired.string="cd"
                else:
                    production.yds_bom_expired = False
        return super(YdsMrpProduction, self)._compute_allowed_product_ids()
