import calendar
from datetime import date, datetime
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare, float_is_zero

import logging

_logger = logging.getLogger(__name__)


class AssetDepreciationLine(models.Model):
    _name = "account.asset.depreciation.line"
    _inherit = "account.asset.depreciation.line"
    amount_linear = fields.Float(string="Amount Linear", digits=0,)
    depreciated_value_linear = fields.Float(
        string="Depreciated Value Linear", digits=0,
    )
    remaining_value_linear = fields.Float(string="Remaining Value Linear",)
    depreciation_difference_linear = fields.Float(
        string="Depreciation Difference Linear"
    )


class AssetsCategoty(models.Model):
    _name = "account.asset.category"
    _inherit = "account.asset.category"

    method_new = fields.Integer(string="One Entry Every (Compare) ")


class AssetsAsset(models.Model):
    _name = "account.asset.asset"
    _inherit = "account.asset.asset"

    method_new = fields.Integer(string="Number of Months in a Period")

    def compute_depreciation_board(self):
        _logger.info("test_fungsi_inherit")
        self.ensure_one()

        posted_depreciation_line_ids = self.depreciation_line_ids.filtered(
            lambda x: x.move_check
        ).sorted(key=lambda l: l.depreciation_date)
        unposted_depreciation_line_ids = self.depreciation_line_ids.filtered(
            lambda x: not x.move_check
        )

        # Remove old unposted depreciation lines. We cannot use unlink() with One2many field
        commands = [
            (2, line_id.id, False) for line_id in unposted_depreciation_line_ids
        ]

        if self.value_residual != 0.0:
            amount_to_depr = (
                residual_amount
            ) = residual_amount_linear = self.value_residual

            # if we already have some previous validated entries, starting date is last entry + method period
            if (
                posted_depreciation_line_ids
                and posted_depreciation_line_ids[-1].depreciation_date
            ):
                last_depreciation_date = fields.Date.from_string(
                    posted_depreciation_line_ids[-1].depreciation_date
                )
                depreciation_date = last_depreciation_date + relativedelta(
                    months=+self.method_period
                )
                depreciation_date = last_depreciation_date + relativedelta(
                    months=+self.method_number
                )
            else:
                # depreciation_date computed from the purchase date
                depreciation_date = self.date
                if self.date_first_depreciation == "last_day_period":
                    # depreciation_date = the last day of the month
                    depreciation_date = depreciation_date + relativedelta(day=31)
                    # ... or fiscalyear depending the number of period
                    if self.method_period == 12:
                        depreciation_date = depreciation_date + relativedelta(
                            month=self.company_id.fiscalyear_last_month
                        )
                        depreciation_date = depreciation_date + relativedelta(
                            day=self.company_id.fiscalyear_last_day
                        )
                        if depreciation_date < self.date:
                            depreciation_date = depreciation_date + relativedelta(
                                years=1
                            )
                elif (
                    self.first_depreciation_manual_date
                    and self.first_depreciation_manual_date != self.date
                ):
                    # depreciation_date set manually from the 'first_depreciation_manual_date' field
                    depreciation_date = self.first_depreciation_manual_date

            total_days = (depreciation_date.year % 4) and 365 or 366
            month_day = depreciation_date.day
            undone_dotation_number = self._compute_board_undone_dotation_nb(
                depreciation_date, total_days
            )

            for x in range(len(posted_depreciation_line_ids), undone_dotation_number):
                sequence = x + 1
                amount = self._compute_board_amount(
                    sequence,
                    residual_amount,
                    amount_to_depr,
                    undone_dotation_number,
                    posted_depreciation_line_ids,
                    total_days,
                    depreciation_date,
                    "linear",
                )
                amount_linear = self._compute_board_amount(
                    sequence,
                    residual_amount_linear,
                    amount_to_depr,
                    undone_dotation_number,
                    posted_depreciation_line_ids,
                    total_days,
                    depreciation_date,
                    "Linear",
                )
                amount = self.currency_id.round(amount)
                amount_linear = self.currency_id.round(amount_linear)
                if float_is_zero(amount, precision_rounding=self.currency_id.rounding):
                    continue
                if float_is_zero(
                    amount_linear, precision_rounding=self.currency_id.rounding
                ):
                    continue
                residual_amount -= amount
                residual_amount_linear -= amount_linear
                vals = {
                    "amount": amount,
                    "amount_linear": amount_linear,
                    "asset_id": self.id,
                    "sequence": sequence,
                    "name": (self.code or "") + "/" + str(sequence),
                    "remaining_value": residual_amount,
                    "remaining_value_linear": residual_amount_linear,
                    "depreciated_value": self.value
                    - (self.salvage_value + residual_amount),
                    "depreciated_value_linear": self.value
                    - (self.salvage_value + residual_amount_linear),
                    "depreciation_difference_linear": (amount - amount_linear),
                    "depreciation_date": depreciation_date,
                }
                commands.append((0, False, vals))

                depreciation_date = depreciation_date + relativedelta(
                    months=+self.method_period
                )
                depreciation_date = depreciation_date + relativedelta(
                    months=+self.method_number
                )

                if month_day > 28 and self.date_first_depreciation == "manual":
                    max_day_in_month = calendar.monthrange(
                        depreciation_date.year, depreciation_date.month
                    )[1]
                    depreciation_date = depreciation_date.replace(
                        day=min(max_day_in_month, month_day)
                    )

                # datetime doesn't take into account that the number of days is not the same for each month
                if (
                    not self.prorata
                    and self.method_period % 12 != 0
                    and self.method_number % 12 != 0
                    and self.date_first_depreciation == "last_day_period"
                ):
                    max_day_in_month = calendar.monthrange(
                        depreciation_date.year, depreciation_date.month
                    )[1]
                    depreciation_date = depreciation_date.replace(day=max_day_in_month)

        self.write({"depreciation_line_ids": commands})

        return True

    def _compute_board_amount(
        self,
        sequence,
        residual_amount,
        amount_to_depr,
        undone_dotation_number,
        posted_depreciation_line_ids,
        total_days,
        depreciation_date,
        method,
    ):
        amount = 0
        if sequence == undone_dotation_number:
            amount = residual_amount
        else:
            if method == "linear":
                amount = amount_to_depr / (
                    undone_dotation_number - len(posted_depreciation_line_ids)
                )
                if self.prorata:
                    amount = amount_to_depr / self.method_period
                if self.prorata:
                    amount_linear = amount_to_depr / self.method_number
                    if sequence == 1:
                        date = self.date
                        if self.method_period % 12 != 0:
                            month_days = calendar.monthrange(date.year, date.month)[1]
                            days = month_days - date.day + 1
                        if self.method_number % 12 != 0:
                            month_days = calendar.monthrange(date.year, date.month)[1]
                            days = month_days - date.day + 1
                            amount = (
                                (amount_to_depr / self.method_period)
                                / month_days
                                * days
                            )
                            amount_linear = (
                                (amount_to_depr / self.method_number)
                                / month_days
                                * days
                            )
                        else:
                            days = (
                                self.company_id.compute_fiscalyear_dates(date)[
                                    "date_to"
                                ]
                                - date
                            ).days + 1
                            amount = (
                                (amount_to_depr / self.method_period)
                                / total_days
                                * days
                            )
                            amount_linear = (
                                (amount_to_depr / self.method_number)
                                / total_days
                                * days
                            )
        return amount
