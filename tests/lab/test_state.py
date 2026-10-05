import unittest

from conformance.lab import state
from conformance.lab.errors import GateError
from tests.lab.helpers import NOW, LabTest


class StateTest(LabTest):
    def test_new_state_is_scoped(self):
        state.new_state(self.tmp, NOW)
        self.assertEqual(state.load_state(self.tmp)["state"], "SCOPED")

    def test_missing_state_is_a_gate_error(self):
        with self.assertRaises(GateError):
            state.load_state(self.tmp)

    def test_every_illegal_transition_is_rejected(self):
        for start in state.STATES:
            for target in state.STATES:
                if target in state.TRANSITIONS[start]:
                    continue
                with self.subTest(start=start, target=target):
                    doc = {"state": start, "history": [], "plan_sha256": None,
                           "plan_published_ref": None, "repository": None}
                    state.save(self.tmp, doc)
                    with self.assertRaises(GateError):
                        state.transition(self.tmp, target, NOW)
                    self.assertEqual(state.load_state(self.tmp)["state"], start)

    def test_legal_path_records_history_and_fields(self):
        state.new_state(self.tmp, NOW)
        for target in ("FROZEN", "RUN", "PACKAGED", "SHARED_PRIVATE", "REVIEWED", "PUBLISHED"):
            state.transition(self.tmp, target, NOW, note=target.lower(), repository="o/r")
        doc = state.load_state(self.tmp)
        self.assertEqual([h["state"] for h in doc["history"]][-1], "PUBLISHED")
        self.assertEqual(len(doc["history"]), 7)
        self.assertEqual(doc["repository"], "o/r")

    def test_require_names_allowed_states(self):
        state.new_state(self.tmp, NOW)
        with self.assertRaisesRegex(GateError, "FROZEN"):
            state.require(self.tmp, "FROZEN")


if __name__ == "__main__":
    unittest.main()
