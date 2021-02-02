from odoo import models, fields, api, exceptions,_
from odoo.exceptions import ValidationError
from collections import defaultdict
import ipdb 
from datetime import datetime

class YdsMrpProduction(models.Model):
    _inherit = "mrp.production"
    yds_bom_expired = fields.Boolean(string="Selected Bill of Material has expired !", readonly=True, Default="False")
    yds_extra_cost = fields.Float(string="Extra Cost",readonly=True, Default=0.0,store=True)
    yds_saved_cost = fields.Float(string="Cost Savings",readonly=True, Default=0.0,store=True)
    yds_expected_cost = fields.Float(string="Expected Cost", readonly=True, Default=0.0,store=True)
    yds_actual_cost = fields.Float(string="Actual Cost", readonly=True, Default=0.0,store=True)
    

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


    def yds_calc_extra_cost(self):
        for production in self:
            production.yds_expected_cost = 0.0
            production.yds_actual_cost = 0.0
            production.yds_saved_cost= 0.0
            production.yds_extra_cost = 0.0
            for move in production.move_raw_ids:
                if move.forecast_availability > move.quantity_done:
                    production.yds_saved_cost+= (move.forecast_availability - move.quantity_done)*move.product_id.standard_price
                elif move.forecast_availability < move.quantity_done:
                    production.yds_extra_cost+= (move.quantity_done - move.forecast_availability)*move.product_id.standard_price
                production.yds_expected_cost += move.forecast_availability*move.product_id.standard_price
                production.yds_actual_cost += move.quantity_done*move.product_id.standard_price


    def button_mark_done(self):
        self.yds_calc_extra_cost()
        # ipdb.set_trace()
        res = super(YdsMrpProduction, self).button_mark_done()
        return res		


    #remove subcontracting extra cost field from measres/filters/groupby..
    @api.model
    def fields_get(self, fields=None):
        #Fields to be added in Filters/Group By
        show = ['extra_cost']
        res = super(YdsMrpProduction, self).fields_get()
        #True = add fields, False = Remove fields
        for field in show:
            res[field]['selectable'] = False
            res[field]['sortable'] = False
            res[field]['exportable'] = False # to hide in export list
            res[field]['store'] = False
        return res
