# Copyright 2020 Tecnativa - Víctor Martínez
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from odoo import api, fields, models, tools



class IrUiMenu(models.Model):
    _inherit = "ir.ui.menu"

    excluded_group_ids = fields.Many2many(
        comodel_name="res.groups",
        relation="ir_ui_menu_excluded_group_rel",
        column1="menu_id",
        column2="gid",
        string="Excluded Groups",
    )

    ## YDS: Modifying store module base_menu_visibility_restriction
    @api.model
    @tools.ormcache("frozenset(self.env.user.groups_id.ids)", "debug")
    def _visible_menu_ids(self, debug=False):
        """ Return the ids of the menu items visible to the user. """
        visible = super()._visible_menu_ids(debug=debug)
        context = {"ir.ui.menu.full_list": True}
        menus = self.with_context(context).browse(visible)
        groups = self.env.user.groups_id
        # YDS : added two lines 
        # checking if the user has menu excluded groups in his/her implied groups 
        # implied_groups -> union(excluded and implied)
        # deattaching the groups from their implied parents by removing the implied_groups,
        # keeping the last group in the tree
        # example: if user has groups (Quality/User->Stock/User->Stock/Admin)-> StockAdmin kept
        # the rest removed if in excluded groupps.
        implied_groups = menus.excluded_group_ids & groups.implied_ids
        groups = groups - implied_groups
        # -------------------------------------------------------------------------------
        visible = menus - menus.filtered(
            lambda menu: menu.excluded_group_ids & groups)
        return set(visible.ids)