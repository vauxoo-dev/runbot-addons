from odoo import fields, models


class RemoteMixin(models.AbstractModel):
    _name = "fwbot.remote.mixin"
    _description = "Remote record mixin"
    _default_timeout = 10

    last_processed = fields.Datetime(readonly=True)

    @property
    def timeout(self):
        return self.env.context.get("timeout", self._default_timeout)
