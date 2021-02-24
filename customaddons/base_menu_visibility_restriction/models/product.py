"""YDS: Hide Product Template "Reordering Rules" and "Putaway Rules" buttons from Inventory User."""
from odoo import _, api, fields, models, SUPERUSER_ID
from odoo.tools.xml_utils import etree

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # override method to hide field if group is stock.group_stock_user
    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        # get view
        res = super(ProductTemplate, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar,
                                                    submenu=submenu)
        if view_type == 'form':
            doc = etree.XML(res['arch'])
            user = self.env.user
            for search in [
                            doc.xpath("//div[@name='button_box']/button[@name='action_view_related_putaway_rules']"),
                            doc.xpath("//div[@name='button_box']/button[@name='action_view_orderpoints'][2]")
                            ]:
                for node in search:
                    if user.has_group('stock.group_stock_user') and not user.has_group('stock.group_stock_manager') and user.id != SUPERUSER_ID:
                        node.set('invisible', 'True')
                        node.set('modifiers', '{"invisible": true}')
            res['arch'] = etree.tostring(doc)
        return res