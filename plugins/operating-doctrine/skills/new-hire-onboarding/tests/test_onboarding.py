import copy
import json
from pathlib import Path
import subprocess
import sys
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "onboarding.py"


class OnboardingTest(unittest.TestCase):
    def invoke(self, request, state, code=0):
        result = subprocess.run(
            [sys.executable, SCRIPT],
            input=json.dumps(request),
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, code, result.stdout + result.stderr)
        result = json.loads(result.stdout)
        self.assertEqual(result["state"], state)
        return result

    def person(self, mode="apply"):
        return {
            "kind": "person",
            "mode": mode,
            "principal": "hire@example.invalid",
            "folders": [
                dict(id=id_, verified=True, can_share=True, complete=True, permissions=[])
                for id_ in ("core", "dept")
            ],
        }

    def test_human_plan_grant_resume_and_noop(self):
        request = self.person("plan")
        self.assertEqual(self.invoke(request, "planned")["folders"][0]["status"], "would_create")
        request["mode"] = "apply"
        self.assertEqual(self.invoke(request, "planned")["folders"][0]["status"], "create")
        acl = dict(
            type="user",
            email="HIRE@example.invalid",
            role="writer",
            id="acl",
            deleted=False,
        )
        request["folders"][0]["permissions"] = [acl]
        self.assertEqual(
            [row["status"] for row in self.invoke(request, "planned")["folders"]],
            ["present", "create"],
        )
        request["folders"][1]["permissions"] = [dict(acl, role="reader")]
        request["folders"][0]["can_share"] = False
        self.invoke(request, "access_verified")
        request["first_use"] = True
        self.invoke(request, "complete")

    def test_drive_write_suppression(self):
        for changed in (
            dict(verified=False),
            dict(complete=False),
            dict(can_share=False),
            dict(
                permissions=[
                    dict(
                        type="user",
                        email="hire@example.invalid",
                        role="reader",
                        id="acl",
                        deleted=False,
                        expires="2099-01-01",
                    )
                ]
            ),
        ):
            with self.subTest(changed=changed):
                request = self.person()
                request["folders"][1].update(changed)
                result = self.invoke(request, "blocked", 1)
                self.assertEqual(result["folders"][0]["status"], "not_attempted")

    def test_same_folder_deduplicates_but_conflicting_metadata_fails(self):
        request = self.person()
        request["folders"][1] = copy.deepcopy(request["folders"][0])
        self.assertEqual(len(self.invoke(request, "planned")["folders"]), 1)
        request["folders"][1]["can_share"] = False
        self.invoke(request, "blocked", 2)

    def test_ai_current_identity_and_first_use(self):
        cores = {"hq-core": "hq", "ep-core": "ep", "ag-core": "ag"}
        request = dict(
            kind="ai",
            mode="plan",
            own_core="ep-core",
            cores=cores,
            department="ep-sales",
            department_folder="sales",
            extras={"ep-outputs": "outputs"},
            observed={},
        )
        self.assertIn("ag-core", self.invoke(request, "planned")["missing"])
        request.update(
            mode="apply", observed=cores | {"ep-sales": "sales", "ep-outputs": "outputs"}
        )
        self.invoke(request, "blocked", 1)
        request.update(principal_verified=True, roots_verified=True)
        self.invoke(request, "access_verified")
        request.update(instructions_verified=True, first_use=True, recovery_verified=True)
        self.invoke(request, "complete")
        request["observed"]["ep-private"] = "private"
        request["observed"]["ep-sales"] = "other"
        del request["observed"]["ag-core"]
        result = self.invoke(request, "blocked", 1)
        self.assertEqual(result["unexpected"], ["ep-private"])
        self.assertEqual(result["misrouted"], ["ep-sales"])
        self.assertEqual(result["missing"], ["ag-core"])

    def test_missing_and_invalid_inputs_do_not_print_input(self):
        self.invoke({"kind": "person", "mode": "apply"}, "blocked", 2)
        self.invoke(dict(self.person(), principal="unnamed"), "blocked", 2)


if __name__ == "__main__":
    unittest.main()
