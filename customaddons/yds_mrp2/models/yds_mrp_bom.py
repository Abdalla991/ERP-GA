from odoo import models, fields, api, exceptions,_
from odoo.exceptions import ValidationError
from collections import defaultdict
import ipdb 
from datetime import datetime


class YdsMrpBom(models.Model):
    _inherit = "mrp.bom"
    yds_start_date = fields.Date(string="Start Date")
    yds_end_date = fields.Date(string="End Date")
    bom_count = fields.Integer(string="Number of invoices", compute="_count_boms", readonly=True)
    yds_total_percent = fields.Float('Total percent',default=0.0000, digits=(12,4))
    yds_total_quantity = fields.Float('Total Quantity',default=0.0000, digits=(12,4))


    @api.depends('bom_line_ids')
    def _count_boms(self):
        self.bom_count = len(self.env['mrp.bom'].search([]))
        for bom in self:
            bom._update_bom_line_custom_fields()
            for bom_line in bom.bom_line_ids:
                bom_line._yds_compute_qty()  



    @api.onchange('bom_line_ids','product_tmpl_id', 'product_qty','product_uom_id')
    def _update_bom_line_custom_fields(self):


        for bom in self:
            bom.yds_total_percent = 0
            bom.yds_total_quantity = 0
            for bom_line in bom.bom_line_ids:
                bom_line.yds_record_product_uom_id = bom.product_uom_id
                bom_line.yds_record_product_uom_name = bom.product_uom_id.name
                bom_line.yds_record_product_qty = bom.product_qty
                bom_line._yds_compute_qty()
                bom.yds_total_percent += bom_line.yds_product_percent
                bom.yds_total_quantity += bom_line.product_qty





class YdsMrpBomLine(models.Model):
    _inherit = "mrp.bom.line"


    yds_product_percent = fields.Float(string='Percentage',store=True)
    yds_product_qty = fields.Float('Quantity', default=1.0, digits='Product Unit of Measure', required=True)

    yds_record_product_uom_id = fields.Integer('Product Unit of Measure')
    yds_record_product_uom_name = fields.Char('Product Unit of Measure')
    yds_record_product_qty = fields.Float('Quantity', default=1.0, digits='Product Unit of Measure', required=True)

    yds_product_uom_id = fields.Integer('Product Unit of Measure2')
    busy_flag = fields.Boolean(string='wait', default=False)

    rounding = fields.Float(string='Rounding Precision', required=True, default=0.01,
    help='Represent the non-zero value smallest coinage (for example, 0.05).')

    rounding_method = fields.Selection(string='Rounding Method', required=True,
        selection=[('UP', 'UP'), ('DOWN', 'DOWN'), ('HALF-UP', 'HALF-UP')],
        default='HALF-UP', help='The tie-breaking rule used for float rounding operations')

    @api.onchange('product_qty')
    def _yds_compute_percent(self):
        for bom_line in self:
            bom_line.yds_product_uom_id = bom_line.product_uom_id
            if bom_line.yds_record_product_qty != 0:
                if bom_line.bom_id.product_uom_id.name == 'kg' and bom_line.product_uom_id.name == 'g':
                    result =  round((bom_line.product_qty / bom_line.bom_id.product_qty / 1000) * 100,4)   
                    bom_line.yds_product_percent = result
                    
                else:
                    result =  round((bom_line.product_qty / bom_line.bom_id.product_qty) * 100,4)   
                    bom_line.yds_product_percent = result


    @api.onchange('yds_product_percent', 'product_uom_id','yds_record_product_uom_id', 'yds_record_product_qty')
    def _yds_compute_qty(self):


        for bom_line in self:
            bom_line.yds_product_uom_id = bom_line.product_uom_id
            if bom_line.yds_product_percent != 0:
                if bom_line.bom_id.product_uom_id.name == 'kg' and bom_line.product_uom_id.name == 'g':
                    bom_line.product_qty = bom_line.yds_product_percent / 100 * bom_line.yds_record_product_qty * 1000
                else:
                    bom_line.product_qty = bom_line.yds_product_percent / 100 * bom_line.yds_record_product_qty
            if bom_line.yds_record_product_qty != 0:
                if bom_line.bom_id.product_uom_id.name == 'kg' and bom_line.product_uom_id.name == 'g':
                    result =  round((bom_line.product_qty / bom_line.bom_id.product_qty / 1000) * 100,4)   
                    bom_line.yds_product_percent = result
                else:
                    result =  round((bom_line.product_qty / bom_line.bom_id.product_qty) * 100,4)   
                    bom_line.yds_product_percent = result



class YdsMrpProduction(models.Model):
    _inherit = "mrp.production"
    yds_bom_expired = fields.Boolean(string="Selected Bill of Material has expired !", readonly=True, Default="False")
    # yds_extra_cost = fields.Float(string="YDS Extra Cost",readonly=True, Default=0.0,store=True)
    # yds_saved_cost = fields.Float(string="YDS Cost Savings",readonly=True, Default=0.0,store=True)
    # yds_total_cost_before = fields.Float(readonly=True, Default=0.0)
    # yds_total_cost_after = fields.Float(readonly=True, Default=0.0)

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


    # def yds_calc_extra_cost(self):
    #     for production in self:
    #         for move in production.move_raw_ids:
    #             if move.forecast_availability > move.quantity_done:
    #                 production.yds_saved_cost+= (move.forecast_availability - move.quantity_done)*move.product_id.standard_price
    #             elif move.forecast_availability < move.quantity_done:
    #                 production.yds_extra_cost+= (move.quantity_done - move.forecast_availability)*move.product_id.standard_price
    #             production.yds_total_cost_before += move.forecast_availability
                    


    def button_mark_done(self):
        # self.yds_calc_extra_cost()
        # ipdb.set_trace()
        res = super(YdsMrpProduction, self).button_mark_done()
        return res		

    #raw_material_production_id -> MO id