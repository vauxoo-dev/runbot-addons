from ..models.repository import Repository
from .common import ForwardBotCase


class TestRepository(ForwardBotCase):
    def setUp(self):
        super().setUp()
        self.model_repo: Repository = self.env["forwardbot_gitlab.repository"]

    def test_get_branch_version(self):
        self.assertEqual(1000.0, self.model_repo.get_branch_version("main"))
        self.assertEqual(1000.0, self.model_repo.get_branch_version("master"))

        self.assertEqual(12.0, self.model_repo.get_branch_version("12.0"))
        self.assertEqual(12.0, self.model_repo.get_branch_version("saas-12"))

        self.assertEqual(16.1, self.model_repo.get_branch_version("16.1"))
        self.assertEqual(16.1, self.model_repo.get_branch_version("saas-16.1"))

        self.assertEqual(-1.0, self.model_repo.get_branch_version("bazinga"))

    def test_get_next_branch(self):
        repository = self.model_repo.create(
            {"remote_id": 5, "stable_branches": "12.0,14.0,15.0,master"}
        )
        self.assertEqual("14.0", repository.get_next_branch("12.0"))
        self.assertEqual("15.0", repository.get_next_branch("14.0"))
        self.assertEqual("master", repository.get_next_branch("15.0"))
        self.assertEqual("", repository.get_next_branch("master"))

    def test_updated_branches(self):
        repository = self.model_repo.create({"remote_id": 4})
        repository.update_branches(
            ["16.0", "master", "14.0", "12", "saas-12.1", "15.0", "13.0"]
        )

        expected_list = ["12", "saas-12.1", "13.0", "14.0", "15.0", "16.0", "master"]
        self.assertEqual(",".join(expected_list), repository.stable_branches)
