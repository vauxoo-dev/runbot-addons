from .common import ForwardBotCase


class TestMergeRequest(ForwardBotCase):
    def test_obtain_from_event_create(self):
        payload = self._gen_payload(50)
        merge_request, created = self.model_mr.obtain_from_event(payload)

        self.assertMergeRequestEquals(payload, merge_request)
        self.assertTrue(created)

    def test_obtain_from_event_read(self):
        payload = self._gen_payload(56)

        merge_request, created = self.model_mr.obtain_from_event(payload)
        self.assertTrue(created)

        read_mr, created = self.model_mr.obtain_from_event(payload)
        self.assertEqual(merge_request, read_mr)
        self.assertFalse(created)

    def test_create_from_event_bad_payload(self):
        bad_payload = {
            "object_attributes": {
                "id": 99,
                "target_branch": "master",
            }
        }

        with self.assertRaisesRegex(ValueError, "missing field"):
            self.env["forwardbot_gitlab.merge.request"].obtain_from_event(bad_payload)

    def test_create_forward_port(self):
        merge_request, _ = self.model_mr.obtain_from_event(self._gen_payload(80))
        merge_request.create_forward_port()

        self.assertEqual("11.0", merge_request.target_branch)
        self.assertEqual("12.0", merge_request.forward_port_id.target_branch)

    def test_forward_port_not_repeated(self):
        merge_request, _ = self.model_mr.obtain_from_event(self._gen_payload(85))

        original_id = merge_request.create_forward_port().id
        self.assertTrue(original_id)

        second_call_id = merge_request.create_forward_port().id
        self.assertEqual(original_id, second_call_id)
