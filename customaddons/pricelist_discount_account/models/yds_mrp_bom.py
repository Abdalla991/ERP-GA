from odoo import models, fields, api, exceptions


class YdsMrpBom(models.Model):
    _inherit = "mrp.bom"


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

            
                




 
