import random
from typing import Dict

from odoo.tests.common import TransactionCase

from ..models.merge_request import MergeRequest


class ForwardBotCase(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.random = random.Random()

    def setUp(self):
        super().setUp()
        self.model_mr: MergeRequest = self.env["forwardbot_gitlab.merge.request"]
        self.env["forwardbot_gitlab.project"].create({"remote_id": 18, "protected_branches": "11.0,12.0,13.0,14.0"})

    def _gen_payload(
        self,
        mr_id: int,
        action: str = "open",
        state: str = "opened",
        title: str = "Test MR",
        source_project: int = 15,
        target_project: int = 18,
        target_branch: str = "11.0",
        event_type: str = "merge_request",
    ) -> Dict:
        return {
            "object_kind": event_type,
            "event_type": event_type,
            "object_attributes": {
                "id": mr_id,
                "iid": mr_id + self.random.randint(1, 100),
                "source_branch": "dev-fwbot",
                "target_branch": target_branch,
                "title": title,
                "state": state,
                "action": action,
                "source_project_id": source_project,
                "target_project_id": target_project,
            },
        }

    def assertMergeRequestEquals(self, data: Dict, record):
        data = data["object_attributes"]

        self.assertEqual(data["state"], record.state)
        self.assertEqual(data["id"], record.global_id)
        self.assertEqual(data["title"], record.name)
        self.assertEqual(data["source_branch"], record.source_branch)
        self.assertEqual(data["target_branch"], record.target_branch)
        self.assertEqual(data["source_project_id"], record.source_project_id)
        self.assertEqual(data["target_project_id"], record.target_project_id.remote_id)
