from odoo import models, fields, api


class geolocation(models.Model):
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