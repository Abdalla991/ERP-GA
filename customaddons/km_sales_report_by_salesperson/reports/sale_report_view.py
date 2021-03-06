from odoo import api, models
from odoo.exceptions import ValidationError


class ReportSalesSalespersonWise(models.AbstractModel):
    _name = 'report.km_sales_report_by_salesperson.sale_report_view'

    @api.model
    def _get_report_values(self, docids, data=None):
        try:
            return {
                'doc_ids': data.get('ids'),
                'doc_model': data.get('model'),
                'data': data['form'],
                'start_date': data['start_date'],
                'end_date': data['end_date'],
            }
        except:
            ValidationError('there is no reports for that salesperson')
