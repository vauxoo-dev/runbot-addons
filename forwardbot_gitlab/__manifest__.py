# Copyright <2023> <Vauxoo info@vauxoo.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    "name": "Forwardbot for Gitlab",
    "summary": "Automatically create forward ports",
    "author": "Vauxoo",
    "website": "https://github.com/Vauxoo/runbot-addons",
    "license": "AGPL-3",
    "category": "Bots",
    "version": "11.0.1.0.0",
    "depends": ["base"],
    "external_dependencies": {"python": ["requests"]},
    "data": ["security/ir.model.access.csv", "data/ir_cron.xml"],
    "installable": True,
}
