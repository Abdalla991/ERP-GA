from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import ipdb

class mrpReport(models.Model):
    _inherit = 'mrp.report'
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


    def print_mrp_report(self):
        for report in self:
            temp_data = []
            print(report.bom_id)
            ipdb.set_trace()

        # bom = self.env['mrp.bom'].search([])
        # boms_groupby_dict = {}
        # for bom in self.bom_id:
        #     filtered_bom = list(filter(lambda x: x.bom_id == salesperson, sales_order))
        #     print('filtered_sale_order ===',filtered_sale_order)
        #     filtered_by_date = list(filter(lambda x: x.date_order >= self.start_date and x.date_order <= self.end_date, filtered_sale_order))
        #     boms_groupby_dict[salesperson.name] = filtered_by_date

