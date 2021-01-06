from odoo import models, fields, api, exceptions
from odoo.exceptions import ValidationError
from collections import defaultdict
import ipdb 
from datetime import datetime

class YdsMrpBom(models.Model):
    _inherit = "mrp.bom"
    start_date = fields.Date(string="Start Date")
    end_date = fields.Date(string="End Date")
    bom_count = fields.Integer(string="Number of invoices", compute="_count_boms", readonly=True)
    yds_total_percent = fields.Float('Total percent',default=0.0000, digits=(12,4))
    yds_total_quantity = fields.Float('Total Quantity',default=0.0000, digits=(12,4))


    @api.depends('bom_line_ids')
    def _count_boms(self):
        self.bom_count = len(self.env['mrp.bom'].search([]))
        # print("count boms entered")
        # print("product", self.bom_line_ids)
        # ipdb.set_trace()
        for bom in self:
            bom._update_bom_line_custom_fields()
            for bom_line in bom.bom_line_ids:
                bom_line._yds_compute_qty()  




    # @api.onchange('bom_line_ids')
    # def _update_for_percent(self):
    #     for bom in self:
    #         for bom_line in bom.bom_line_ids:
    #             print("entered new")
    #             bom_line.yds_record_product_uom_id = bom.product_uom_id
    #             bom_line.yds_record_product_uom_name = bom.product_uom_id.name


    @api.onchange('bom_line_ids','product_tmpl_id', 'product_qty','product_uom_id')
    def _update_bom_line_custom_fields(self):


        for bom in self:
            bom.yds_total_percent = 0
            bom.yds_total_quantity = 0
            for bom_line in bom.bom_line_ids:
                bom_line.yds_record_product_uom_id = bom.product_uom_id
                bom_line.yds_record_product_uom_name = bom.product_uom_id.name
                # if bom_line.busy_flag == False:
                bom_line.yds_record_product_qty = bom.product_qty
                bom_line._yds_compute_qty()
                bom.yds_total_percent += bom_line.yds_product_percent
                bom.yds_total_quantity += bom_line.product_qty
                # print(self.bom_count)


            # print("total:", bom.yds_total_percent)



class YdsMrpBomLine(models.Model):
    _inherit = "mrp.bom.line"


    yds_product_percent = fields.Float(string='Percentage',store=True , default=0.0000, digits=(12,4))
    yds_product_qty = fields.Float('Quantity', default=1.0, digits='Product Unit of Measure', required=True)

    yds_record_product_uom_id = fields.Integer('Product Unit of Measure')
    yds_record_product_uom_name = fields.Char('Product Unit of Measure')
    yds_record_product_qty = fields.Float('Quantity', default=1.0, digits='Product Unit of Measure', required=True)

    yds_product_uom_id = fields.Integer('Product Unit of Measure2')
    busy_flag = fields.Boolean(string='wait', default=False)

    @api.onchange('product_qty')
    def _yds_compute_percent(self):
        for bom_line in self:
            bom_line.yds_product_uom_id = bom_line.product_uom_id
            if bom_line.yds_record_product_qty != 0:
                print("comp percent", bom_line.yds_record_product_uom_name,bom_line.product_uom_id.name )
                if bom_line.yds_record_product_uom_name == 'kg' and bom_line.product_uom_id.name == 'g':
                    bom_line.yds_product_percent = bom_line.product_qty * 100 / bom_line.yds_record_product_qty / 1000
                else:
                    bom_line.yds_product_percent = bom_line.product_qty * 100 / bom_line.yds_record_product_qty


###########################################################################################################
    # @api.onchange('product_qty')
    # def _yds_compute_percent(self):
    #     for bom_line in self:
    #         bom_line.yds_product_uom_id = bom_line.product_uom_id
    #         if bom_line.yds_record_product_qty != 0:
    #             bom_line.yds_product_percent = bom_line.product_qty * 100 / bom_line.yds_record_product_qty

    # @api.onchange('yds_product_percent', 'product_uom_id', 'yds_record_product_uom_id', 'yds_record_product_qty')
    # def _yds_compute_qty(self):
    #     for bom_line in self:
    #         bom_line.yds_product_uom_id = bom_line.product_uom_id
    #         if bom_line.yds_product_percent != 0:
    #             bom_line.product_qty = bom_line.yds_product_percent / 100 * bom_line.yds_record_product_qty
    #         if bom_line.yds_record_product_qty != 0:
    #             bom_line.yds_product_percent = bom_line.product_qty * 100 / bom_line.yds_record_product_qty

###########################################################################################################

    @api.onchange('yds_product_percent', 'product_uom_id', 'yds_record_product_uom_id', 'yds_record_product_qty')
    def _yds_compute_qty(self):
        for bom_line in self:
            bom_line.yds_product_uom_id = bom_line.product_uom_id
            if bom_line.yds_product_percent != 0:
                if bom_line.yds_record_product_uom_name == 'kg' and bom_line.product_uom_id.name == 'g':
                    bom_line.product_qty = bom_line.yds_product_percent / 100 * bom_line.yds_record_product_qty * 1000
                else:
                    bom_line.product_qty = bom_line.yds_product_percent / 100 * bom_line.yds_record_product_qty
            if bom_line.yds_record_product_qty != 0:
                print("comp percent", bom_line.yds_record_product_uom_name,bom_line.product_uom_id.name )
                if bom_line.yds_record_product_uom_name == 'kg' and bom_line.product_uom_id.name == 'g':
                    bom_line.yds_product_percent = bom_line.product_qty * 100 / bom_line.yds_record_product_qty / 1000
                else:
                    bom_line.yds_product_percent = bom_line.product_qty * 100 / bom_line.yds_record_product_qty





    # @api.onchange('yds_product_percent','product_uom_id', 'yds_record_product_uom_id')
    # def _yds_check_uom(self):
    #     for bom_line in self:
    #             if bom_line.yds_product_percent != 0.0:
    #                  if bom_line.yds_product_uom_id != bom_line.yds_record_product_uom_id: 
    #                      raise ValidationError("The component doesn't have the same uom of the product.")

class YdsMrpProduction(models.Model):
    _inherit = "mrp.production"
    yds_bom_expired = fields.Boolean(string="Selected Bill of Material has expired !", readonly=True, Default="False")
    
    @api.depends('product_id', 'bom_id', 'company_id')
    def _compute_allowed_product_ids(self):
    
        for production in self: 
            if production.bom_id:
                if production.bom_id.start_date and production.bom_id.end_date:
                    start = datetime.strptime(str(production.bom_id.start_date), '%Y-%m-%d')
                    end = datetime.strptime(str(production.bom_id.end_date), '%Y-%m-%d')
                    current = datetime.strptime(str(datetime.now().date()), '%Y-%m-%d')
                    if start <= current and end > current :
                        production.yds_bom_expired = False
                        print(str(production.yds_bom_expired))
                    else:
                        production.yds_bom_expired = True
                        print(str(production.yds_bom_expired))

        return super(YdsMrpProduction, self)._compute_allowed_product_ids()

    def button_mark_done(self):
        for move in self.move_raw_ids:
            if move.forecast_availability < move.quantity_done:
                raise ValidationError('Please check the availability for all components.')
                return
        res = super(YdsMrpProduction, self).button_mark_done()
        return res