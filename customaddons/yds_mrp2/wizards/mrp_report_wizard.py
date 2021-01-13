from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import ipdb, math

class mrpReport(models.TransientModel):
    _name = 'mrp.report'
    _description = 'MRP Report'

    # name = fields.Char(string='Pro')
    product_id = fields.Many2one('product.product', string='Product', ondelete='cascade', help="Select a product which will use analytic account specified in analytic default (e.g. create new customer invoice or Sales order if we select this product, it will automatically take this as an analytic account)")
    bom_id = fields.Many2one(
        'mrp.bom', 'Bill of Material',
        domain="""[
        '&',
                '|',
                    ('product_id','=',product_id),
                    '&',
                        ('product_tmpl_id.product_variant_ids','=',product_id),
                        ('product_id','=',False),
        ('type', '=', 'normal')]""",
        check_company=True,
        help="Bill of Materials allow you to define the list of required components to make a finished product.")

    start_date = fields.Date(string='Start Date',related='bom_id.yds_start_date')
    end_date = fields.Date(string='End Date',related='bom_id.yds_end_date')
    product_qty = fields.Float(string='Quantity', related='bom_id.product_qty')


    qty_producing = fields.Float(string='Quantity to produce')




    def print_mrp_report(self):

        all_boms = self.env['mrp.bom'].search([])
        boms_groupby_dict = {}
        for bom in self.bom_id:
            filtered_bom = list(filter(lambda x: x.id == bom.id, all_boms))
            boms_groupby_dict["bom"] = filtered_bom



        final_dist = {}
        bom_data = []
        chosen_bom =  boms_groupby_dict.get("bom")[0]

        if self.qty_producing <= 0.0:
            chosen_product_qty = chosen_bom.product_qty
        else:
            chosen_product_qty = self.qty_producing

        bom_data.append(chosen_bom.product_tmpl_id.name)
        bom_data.append(chosen_product_qty)
        bom_data.append(chosen_bom.product_uom_id.name)
        bom_data.append(chosen_bom.code)
        bom_data.append(chosen_bom.type)
        bom_data.append(self.start_date)
        bom_data.append(self.end_date)
        bom_data.append(chosen_bom.company_id.name)
        bom_data.append(chosen_bom.product_tmpl_id.default_code)

     
        
        bom_lines = []
        available_units_of_product_arr = []
        for bom_line in chosen_bom.bom_line_ids:
            bom_line_data = []
            component_availability = {}
            available_units_of_product = 0

            if chosen_product_qty == 0:
                raise ValidationError('Product quantity cannot be zero')
            if bom_line.product_qty == 0:
                raise ValidationError('Component quantity cannot be zero')

            required_qty_for_one_kg =  bom_line.product_qty / chosen_bom.product_qty 
            chosen_component_quantity = bom_line.product_qty * chosen_product_qty / chosen_bom.product_qty

            #calculations
            if bom_line.product_id.qty_available <= 0:
                component_availability['id'] = 0
                component_availability['name'] = 'not available'
                available_units_of_product = 0
                available_units_of_product_arr.append(0)
            else:
                component_availability['id'] = 1
                component_availability['name'] = 'available'
                available_units_of_product = bom_line.product_id.qty_available / required_qty_for_one_kg
                available_units_of_product_arr.append(available_units_of_product)

            

            bom_line_data.append(bom_line.product_id.name)
            bom_line_data.append(chosen_component_quantity)
            bom_line_data.append(bom_line.product_id.qty_available)
            bom_line_data.append(bom_line.yds_product_percent)
            bom_line_data.append(bom_line.product_uom_id.name)
            bom_line_data.append(available_units_of_product)
            bom_lines.append(bom_line_data)


        
        final_available_units_of_product = min(available_units_of_product_arr)
        


            

        bom_data.append(final_available_units_of_product)
        to_loop = []
        to_loop.append(bom_data)

        final_dist["bom"] = to_loop
        final_dist["bom_lines"] = bom_lines
        # print("final dist: ",final_dist)
        # ipdb.set_trace()
        datas = {
            'ids': self,
            'model': 'mrp.report',
            'form': final_dist
        }
        return self.env.ref('yds_mrp2.action_report_mrp').report_action([], data=datas)

