#!/usr/bin/env python3
"""Offline SSH deletion decisions. Command strings are never executed."""

import json
import os
from pathlib import Path
import shlex
import subprocess
import tempfile
import unittest


HOOKS = Path(__file__).resolve().parents[1]


class SSHDeletionApprovalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="ssh-deletion-approval-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.notes = self.root / "notes"
        self.notes.mkdir()
        self.calls = self.root / "ssh-calls"
        fake = self.root / "ssh"
        fake.write_text(
            "#!/bin/sh\n"
            'printf "%s\\n" "$*" >> "$SSH_FAKE_CALLS"\n'
            '[ "$1" = "-G" ] || exit 255\n'
            'for target do :; done\n'
            'case "$target" in\n'
            '  *@*) user="${target%%@*}" ;;\n'
            '  *) user=ember ;;\n'
            'esac\n'
            'printf "user %s\\nhostname %s\\n" "$user" "${target##*@}"\n'
        )
        fake.chmod(0o700)
        self.env = os.environ.copy()
        for name in (
            "PRE_TOOL_USE_OFF", "BASH_ENV", "ENV", "GUARD_DEADLINE_SECONDS",
            "DELETION_APPROVAL_SSH_CONFIG",
        ):
            self.env.pop(name, None)
        self.env.update(
            HOME=str(self.root),
            DELETION_APPROVAL_DIR=str(self.notes),
            DELETION_APPROVAL_LOG=str(self.root / "audit.log"),
            DELETION_APPROVAL_LIB=str(HOOKS / "lib/deletion-approval-common.sh"),
            DELETION_APPROVAL_SSH_BIN=str(fake),
            SSH_FAKE_CALLS=str(self.calls),
        )

    def tearDown(self):
        if self.calls.exists():
            self.assertTrue(all(
                call.startswith("-G ") for call in self.calls.read_text().splitlines()
            ), "the fake must only receive offline configuration lookups")
        self.assertFalse(list(self.notes.glob("*.claimed.*")))

    def grant(self, path="/tmp/scratch-x", host="ember"):
        args = [
            "bash", str(HOOKS / "deletion-approval-note.sh"), "grant",
            "--target", path, "--quote", "synthetic test approval, not live authority",
            "--session", "offline SSH guard test",
        ]
        if host is not None:
            args.extend(["--host", host])
        result = subprocess.run(
            args, env=self.env, cwd=HOOKS, text=True, capture_output=True, timeout=10
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def decide(self, command, expected, missing_library=False, process_cwd=None):
        env = self.env.copy()
        if missing_library:
            env["DELETION_APPROVAL_LIB"] = str(self.root / "missing-library")
        result = subprocess.run(
            ["bash", str(HOOKS / "pre-tool-use-enforcement.sh")],
            input=json.dumps({
                "tool_name": "Bash", "tool_input": {"command": command},
                "cwd": str(self.root), "session_id": "offline-ssh-test",
            }),
            env=env, cwd=process_cwd or HOOKS, text=True, capture_output=True, timeout=12,
        )
        self.assertEqual(result.returncode, expected, (command, result.stderr))
        output = json.loads(result.stdout) if result.stdout else {}
        decision = output.get("hookSpecificOutput", {}).get("permissionDecision")
        self.assertEqual(decision, "deny" if expected == 2 else None)
        return output

    def test_required_delete_and_single_use(self):
        command = "ssh ember 'rm -rf /tmp/scratch-x'"
        self.decide(command, 2)
        self.grant()
        output = self.decide(command, 0)
        self.assertIn("consumed", output["hookSpecificOutput"]["additionalContext"])
        self.assertEqual(list(self.notes.iterdir()), [])
        self.decide(command, 2)
        audit = (self.root / "audit.log").read_text()
        self.assertIn("[ALLOW]", audit)
        self.assertIn("[CONSUMED]", audit)
        self.assertIn("ember@ember:/tmp/scratch-x", audit)

    def test_host_path_and_local_notes_are_isolated(self):
        self.grant()
        for command in (
            "ssh other-mac 'rm -rf /tmp/scratch-x'",
            "ssh root@ember 'rm -rf /tmp/scratch-x'",
            "ssh ember 'rm -rf /tmp/scratch-y'",
            "ssh ember 'rm -rf /tmp/scratch-x/child'",
            "ssh ember 'rm -rf /tmp/scratch-x /tmp/unapproved'",
        ):
            with self.subTest(command=command):
                self.decide(command, 2)
                self.assertEqual(len(list(self.notes.glob("*.json"))), 1)
        self.decide("ssh ember 'rm -rf /tmp/scratch-x'", 0)
        self.grant(host=None)
        self.decide("ssh ember 'rm -rf /tmp/scratch-x'", 2)
        self.assertEqual(len(list(self.notes.glob("*.json"))), 1)

    def test_expired_note_is_not_consumed(self):
        self.grant()
        note = next(self.notes.glob("*.json"))
        data = json.loads(note.read_text())
        data["expires_epoch"] = 1
        note.write_text(json.dumps(data))
        self.decide("ssh ember 'rm -rf /tmp/scratch-x'", 2)
        self.assertTrue(note.exists())

    def test_read_only_needs_no_note_or_login_lookup(self):
        for missing in (False, True):
            for command in (
                "ssh ember 'ls ~'",
                "ssh ember 'ls ~/.trash | wc -l'",
                "ssh ember 'ls ~ # rm is only a comment'",
                "ssh ember 'mv /tmp/scratch-x /tmp/renamed-x'",
            ):
                with self.subTest(command=command, missing_library=missing):
                    # Without the parser, keep the existing conservative hold
                    # on pipes and deletion words even inside read-only text.
                    expected = 2 if missing and ("|" in command or "#" in command) else 0
                    self.decide(command, expected, missing_library=missing)
        self.assertFalse(self.calls.exists())

    def test_trash_moves_require_source_note_once(self):
        for destination in (
            "~/.Trash/", "~/.trash/", "/Users/ember/.TRASH/",
            "/Volumes/Backup/.Trashes/501/",
            "/volumes/Backup/.trashes/501/",
        ):
            with self.subTest(destination=destination):
                command = f"ssh ember 'mv /tmp/scratch-x {destination}'"
                self.decide(command, 2)
                self.grant()
                self.decide(command, 0)
                self.assertEqual(list(self.notes.iterdir()), [])
                self.decide(command, 2)

    def test_trash_destination_note_does_not_approve_source(self):
        self.grant(path="~/.Trash/scratch-x")
        self.decide("ssh ember 'mv /tmp/scratch-x ~/.Trash/scratch-x'", 2)
        self.assertEqual(len(list(self.notes.glob("*.json"))), 1)

    def test_trash_move_with_comment_is_not_approvable(self):
        self.grant()
        for command in (
            "ssh ember 'mv /tmp/scratch-x ~/.Trash # cleanup'",
            "ssh ember 'mv /tmp/scratch-x ~/.trash # cleanup'",
            "ssh ember 'mv /tmp/scratch-x ~/.Trash # ; echo done'",
        ):
            with self.subTest(command=command):
                self.decide(command, 2)
                self.assertEqual(len(list(self.notes.glob("*.json"))), 1)
        self.decide("ssh ember 'mv /tmp/scratch-x ~/.Trash'", 0)

    def test_quoted_hash_in_exact_source_is_approvable(self):
        self.grant(path="/tmp/#scratch-x")
        self.decide('ssh ember "mv \'/tmp/#scratch-x\' ~/.Trash"', 0)
        self.assertEqual(list(self.notes.iterdir()), [])

    def test_escaped_space_before_literal_hash_is_approvable(self):
        command = "ssh ember 'mv /tmp/a\\ #b ~/.Trash'"
        self.decide(command, 2)
        self.grant(path="/tmp/a #b")
        self.decide("ssh ember 'mv /tmp/a\\ #b ~/.Trash # cleanup'", 2)
        self.assertEqual(len(list(self.notes.glob("*.json"))), 1)
        self.decide(command, 0)
        self.assertEqual(list(self.notes.iterdir()), [])
        self.decide(command, 2)

    def test_trash_lookalike_names_are_ordinary_renames(self):
        for destination in (
            "~/.trash-backup", "~/.trashcan", "~/.Trashes.old",
            "/tmp/.trash-report/x",
        ):
            for prefix in ("", "env "):
                command = f"ssh ember '{prefix}mv /tmp/scratch-x {destination}'"
                for missing in (False, True):
                    with self.subTest(command=command, missing_library=missing):
                        self.decide(command, 0, missing_library=missing)
        self.assertFalse(self.calls.exists())

    def test_missing_library_blocks_trash_moves(self):
        for command in (
            "ssh ember 'mv /tmp/scratch-x ~/.trash/'",
            "ssh ember 'mv /tmp/scratch-x /Volumes/Backup/.TRASHES/501/'",
            "ssh ember 'mv /tmp/scratch-x ~/.Trash*'",
            "ssh ember 'mv /tmp/scratch-x {~/.Trash,~/.Trash}'",
            "ssh ember 'mv /tmp/scratch-x ~/.Trash${suffix}'",
        ):
            with self.subTest(command=command):
                self.decide(command, 2, missing_library=True)
        self.assertFalse(self.calls.exists())

    def test_unreadable_targets_never_spend_a_note(self):
        self.grant()
        for command in (
            "ssh ember 'rm -rf /tmp/scratch-*'",
            "ssh ember 'rm -rf /tmp/../scratch-x'",
            "ssh ember 'rm -rf scratch-x'",
            "ssh ember 'sudo rm -rf /tmp/scratch-x'",
            "ssh ember 'rm -rf /tmp/scratch-x; rm -rf /tmp/other'",
            "ssh -o Hostname=other-mac ember 'rm -rf /tmp/scratch-x'",
            "ssh ember 'mv /tmp/scratch-* ~/.trash/'",
            "ssh ember 'mv /tmp/scratch-x ~/.Trash*'",
            "ssh ember 'env mv /tmp/scratch-x ~/.Trash*'",
            "ssh ember 'mv /tmp/scratch-x {~/.Trash,~/.Trash}'",
            "ssh ember 'mv /tmp/scratch-x ~/.Trash${suffix}'",
        ):
            with self.subTest(command=command):
                self.decide(command, 2)
                self.assertEqual(len(list(self.notes.glob("*.json"))), 1)

    def test_late_security_finding_blocks_with_and_without_library(self):
        command = "ssh ember 'P=$HOME/; mv /tmp/x ${P}.Trash'"
        for missing in (False, True):
            with self.subTest(missing_library=missing):
                self.decide(command, 2, missing_library=missing)
        self.assertFalse(self.calls.exists())

    def test_known_non_trash_destinations_preserve_ordinary_moves(self):
        for command in (
            'ssh ember \'mv "/tmp/$NAME" /tmp/archive\'',
            "ssh ember 'mv /tmp/x /tmp/y; true'",
            'ssh ember \'SRC=/tmp/x; mv -- "${SRC}" /tmp/archive\'',
            'ssh ember \'env mv -- "$SRC" /tmp/archive\'',
            'ssh ember \'command mv -- "$SRC" ~/.trash-backup\'',
            'ssh ember \'mv -- "$SRC" "/tmp/archive with spaces"\'',
            "ssh linux 'mv -- * /tmp/archive'",
            'ssh ember \'mv -- /tmp/$SRC /tmp/archive\'',
            'ssh ember \'mv "/tmp/${SRC}" /tmp/archive\'',
        ):
            with self.subTest(command=command):
                self.decide(command, 0)
                # No parser is available in the missing-library fallback, so
                # it deliberately keeps holding these nonliteral scripts.
                self.decide(command, 2, missing_library=True)
        self.assertFalse(self.calls.exists())

    def test_read_only_parameter_arguments_still_pass(self):
        for command in (
            'ssh ember \'ls "$HOME"\'',
            'ssh ember \'echo "$D"\'',
            'ssh ember \'printf %s "$NAME"\'',
        ):
            for missing in (False, True):
                with self.subTest(command=command, missing_library=missing):
                    self.decide(command, 0, missing_library=missing)
        self.assertFalse(self.calls.exists())

    def test_literal_local_commands_keep_parameter_arguments_and_data(self):
        for command in (
            'printf "%s\\n" "$VALUE"',
            'A="s s"; printf %s "$A"',
            'printf "%s" "; $VALUE"',
            'echo "$(pwd)" "$HOME"',
            'command -v "$NAME"',
            '2>"$OUT" printf %s "$VALUE"',
            'cat <(printf %s "$VALUE")',
            'echo $((1 << 2)) "$VALUE"',
            '(( 1 << 2 )); printf %s "$VALUE"',
            'printf %s "$VALUE" # $(not-a-command)',
            "cat <<'EOF'\n$CMD ember 'mv /tmp/x \"$D\"'\nEOF",
            "cat <<EOF\n$DATA\nEOF",
            "python3 - <<'PY'\nprint(\"$HOME\")\nPY",
            'cat <<< "$VALUE"',
            "find /tmp -maxdepth 0 -exec printf %s \"$VALUE\" ';'",
            "alias show='printf %s'; show \"$VALUE\"",
            'trap -p "$SIGNAL"',
            'trap -l "$SIGNAL"',
            'trap \'printf %s "$VALUE"\' EXIT',
            "bash <<'EOF'\nprintf %s \"$VALUE\"\nEOF",
            'bash /tmp/readonly-script "$VALUE"',
            'printf %s "$VALUE" | bash -c \'printf %s "$1"\' _ "$VALUE"',
            'printf %s "(inert data)|value"',
            'printf %s "|" | cat',
        ):
            for missing in (False, True):
                with self.subTest(command=command, missing_library=missing):
                    self.decide(command, 0, missing_library=missing)
        self.assertFalse(self.calls.exists())

    def test_python_helpers_ignore_cwd_and_pythonpath_modules(self):
        # Inert fixture: it only exits successfully if an unisolated parser
        # mistakenly imports this controlled module instead of the stdlib.
        (self.root / "shlex.py").write_text("raise SystemExit(0)\n")
        self.env["PYTHONPATH"] = str(self.root)
        for command in (
            "A=ss; ${A}h ember 'mv /tmp/x ~/.Trash'",
            'ssh ember \'"$A"v /tmp/x "$D"\'',
        ):
            for missing in (False, True):
                with self.subTest(command=command, missing_library=missing):
                    self.decide(command, 2, missing_library=missing, process_cwd=self.root)
        self.assertFalse(self.calls.exists())

    def test_wrapper_control_fields_keep_expansion_provenance(self):
        commands = [
            # Exact reviewed input, plus the same cardinality error in other
            # control slots. These strings are only serialized as hook JSON.
            'A=s; X="VAR ${A}sh"; env -u $X ember \'rm -rf /tmp/x\'',
        ]
        for value in ('$X', '/tmp/$X', '""$X', '"$@"', '"${ARGS[@]}"',
                      '${EMPTY}', '*', '{VAR,other}'):
            for wrapper in ('env -u', 'env --unset=', 'sudo -u',
                            'nice -n', 'timeout'):
                joiner = '' if wrapper.endswith('=') else ' '
                core = f"{wrapper}{joiner}{value} ember 'rm -rf /tmp/x'"
                for outer in ('', 'command '):
                    commands.append(f'S=ss; X="VAR ${{S}}h"; {outer}{core}')
        commands.extend((
            'S=ss; X="VAR ${S}h"; find /tmp -maxdepth 0 -exec env -u $X '
            "ember 'rm -rf /tmp/x' ';'",
            'S=ss; X="1 ${S}h"; timeout -k $X 1 ember \'rm -rf /tmp/x\'',
        ))
        self.grant(path="/tmp/x")
        before = self.calls.read_text()
        notes_before = {p.name: p.read_bytes() for p in self.notes.glob("*.json")}
        for command in commands:
            for missing in (False, True):
                with self.subTest(command=command, missing_library=missing):
                    self.decide(command, 2, missing_library=missing)
                    self.assertEqual(len(list(self.notes.glob("*.json"))), 1)
        self.assertEqual(self.calls.read_text(), before)
        self.assertEqual({p.name: p.read_bytes() for p in self.notes.glob("*.json")}, notes_before)
        self.decide("ssh ember 'rm -rf /tmp/x'", 0)
        self.assertEqual(list(self.notes.iterdir()), [])
        self.decide("ssh ember 'rm -rf /tmp/x'", 2)

    def test_reevaluated_operands_are_code_not_quoted_data(self):
        target = 'x[$(${S}h ember "rm -rf /tmp/x")]'
        cores = (
            f"printf -v '{target}' 1",
            f"printf -v OUT -v '{target}' 1",
            f"printf '%s%n' data '{target}'",
            f"printf '%3n' '{target}'",
            f"read -r '{target}' </dev/null",
            f"read -a '{target}' </dev/null",
            f"getopts ab '{target}'",
            f"wait -p '{target}'",
            f"wait -np'{target}'",
            f"unset '{target}'",
            f"declare '{target}=1'",
            f"declare -n ref='{target}'",
            f"let '{target}'",
            f"[[ -v '{target}' ]]",
            f"mapfile -C '${{S}}h ember \"rm -rf /tmp/x\"' -c 1 OUT",
            f"readarray -C '${{S}}h ember \"rm -rf /tmp/x\"' -c 1 OUT",
            f"declare -i COUNT; COUNT='{target}'",
            f"EXPR='{target}'; let EXPR",
            f"EXPR='{target}'; echo $((EXPR))",
            f"declare -i COUNT; printf -v COUNT %s '{target}'",
            f"declare -n ref='{target}'; ref=value",
            'printf -v "$DESTINATION" %s data',
            'printf "$FORMAT" "$ARGUMENT"',
            'let "$EXPRESSION"',
            'mapfile -C "$CALLBACK" OUT',
            'complete -C "$CALLBACK" show',
            'complete -C"$CALLBACK" show',
            'compgen -C "$CALLBACK" show',
            "bind -x '\"key\":${S}h ember \"rm -rf /tmp/x\"'",
        )
        commands = [
            # Preserve the exact reported local reproduction.
            f"S=s; {cores[0]}",
        ]
        for core in cores:
            script = f"S=ss; {core}"
            commands.extend((
                script,
                "bash -c " + shlex.quote(script),
                "ssh ember " + shlex.quote(script),
            ))
        commands.extend((
            f"S=ss; command builtin {cores[0]}",
            "find /tmp -maxdepth 0 -exec bash -c " + shlex.quote(f"S=ss; {cores[0]}") + " ';'",
            f"S=ss; alias save='printf -v'; save '{target}' 1",
            "ssh ember printf '%s;' '${S}h ember \"rm -rf /tmp/x\"'",
            'ssh ember printf %s "$VALUE"',
        ))
        self.grant(path="/tmp/x")
        before = self.calls.read_text()
        for command in commands:
            for missing in (False, True):
                with self.subTest(command=command, missing_library=missing):
                    self.decide(command, 2, missing_library=missing)
                    self.assertEqual(len(list(self.notes.glob("*.json"))), 1)
        self.assertEqual(self.calls.read_text(), before)
        self.decide("ssh ember 'mv /tmp/x ~/.Trash'", 0)
        self.assertEqual(list(self.notes.iterdir()), [])

    def test_empty_attached_control_can_change_the_next_role(self):
        target = 'x[$(${S}h ember "rm -rf /tmp/x")]'
        for command in (
            'S=ss; E=""; env -u"$E" VAR ${S}h ember "rm -rf /tmp/x"',
            'S=ss; E=""; nice -n"$E" 1 ${S}h ember "rm -rf /tmp/x"',
            f'S=ss; E=""; read -p"$E" -p \'{target}\' OUT',
            f"declare -i NUMBER; declare -n REF=NUMBER; REF='{target}'",
            f"declare -i NUMBER; printf -v NUMBER '{target}'",
            'declare -i NUMBER; printf -v NUMBER \'$(%s)\' '
            '\'ssh ember "rm -rf /tmp/x"\'',
        ):
            for missing in (False, True):
                with self.subTest(command=command, missing_library=missing):
                    self.decide(command, 2, missing_library=missing)
        self.assertFalse(self.calls.exists())

    def test_operand_roles_preserve_passive_data_and_local_compatibility(self):
        target = 'x[$(${S}h ember "rm -rf /tmp/x")]'
        commands = (
            f"printf %s '{target}'",
            f"printf -v OUT %s '{target}'",
            f"read -r -p '{target}' OUT",
            "printf -v OUT '%s:%s' \"$FIRST\" \"$SECOND\"",
            "printf '%%n %s' \"$VALUE\"",
            "printf '%(%Y%n)T' -1",
            'printf "%*s%n" 2 "$VALUE" OUT',
            "printf '%(%Y-%m-%d)T' -1",
            "read -r OUT",
            "read -r OUT </dev/null",
            "read -r OUT</dev/null",
            'read -r -p"Prompt: $PROMPT" OUT </dev/null',
            "printf -vOUT %s \"$VALUE\"",
            "printf -v OUT -- -v \"$VALUE\"",
            "unset 'x[0]'",
            "let 'COUNT+=1'",
            'env -u "$NAME" printf %s "$VALUE"',
            'env --unset="$NAME" printf %s "$VALUE"',
            'env -u"PREFIX$NAME" printf %s "$VALUE"',
            'timeout "$DURATION" printf %s "$VALUE"',
            'nice -n "$PRIORITY" printf %s "$VALUE"',
            'find /tmp -maxdepth 0 -exec env -u "$NAME" '
            'printf %s "$VALUE" \';\'',
            # Quoting a scalar is sufficient for a passive/control-value field,
            # not permission to treat a variable/subscript or CODE role as DATA.
            'printf %s "$FORMAT" "$DESTINATION" "$CALLBACK"',
            "alias save='printf -v'; save OUT %s \"$VALUE\"",
            "mapfile -C 'printf %s' -c 1 OUT",
            "complete -C 'printf %s' show",
            'complete -G -C -- "$NAME"',
            'complete -p "$NAME"',
            "bind -x '\"key\":printf %s \"$VALUE\"'",
            'ssh ember printf %s \'"$NAME"\'',
            "declare -i COUNT; COUNT=1",
            'declare -i COUNT; printf -v COUNT %d "$NUMBER"',
            'declare TEXT="$VALUE"; printf %s "$TEXT"',
            'EXPR="COUNT+=1"; let EXPR',
            "nice --help",
            "env --version",
            "source /tmp/readonly-source",
            ". /tmp/readonly-source",
            'env printf "$FORMAT" "$VALUE"',
            'find /tmp -maxdepth 0 -exec printf "$FORMAT" "$VALUE" \';\'',
            'ssh ember \'printf -v OUT %s "$NAME"\'',
            'ssh ember \'printf "%%n %s" "$NAME"\'',
        )
        for command in commands:
            for missing in (False, True):
                with self.subTest(command=command, missing_library=missing):
                    self.decide(command, 0, missing_library=missing)
        self.assertFalse(self.calls.exists())

    def test_long_commands_cannot_short_circuit_lexical_gates(self):
        # Force pipe-buffer overflow after an early match. grep -q must not
        # turn SIGPIPE from its producer into a false condition under pipefail.
        padding = "\n#" + " " * 100000
        for command in (
            "A=ss; ${A}h ember 'rm -rf /tmp/x'",
            "ssh ember 'rm -rf /tmp/x'",
        ):
            for missing in (False, True):
                with self.subTest(program=command, missing_library=missing):
                    self.decide(command + padding, 2, missing_library=missing)
                    self.assertEqual(list(self.notes.glob("*.json")), [])
        for missing in (False, True):
            with self.subTest(read_only=True, missing_library=missing):
                self.decide('ssh ember \'ls "$HOME"\'' + padding, 0, missing_library=missing)

    def test_dynamic_move_destinations_are_never_approvable(self):
        # All are data sent to the hook, never commands run by this test.
        commands = (
            "ssh ember 'P=$HOME/; mv /tmp/x ${P}.Trash'",
            "ssh ember 'P=$HOME/ && mv /tmp/x ${P}.Trash'",
            "ssh ember 'false || mv /tmp/x ${P}.Trash'",
            "ssh ember 'P=$HOME/; /bin/mv /tmp/x ${P}.Trash'",
            "ssh ember 'P=$HOME/; env mv /tmp/x ${P}.Trash'",
            "ssh ember 'mv /tmp/x \"${P}.Trash\"'",
            "ssh ember 'mv /tmp/x ${P:-$HOME/}.Trash'",
            "ssh ember 'mv /tmp/x ${P:0}.Trash'",
            "ssh ember 'mv /tmp/x ${P[0]}.Trash'",
            "ssh ember 'mv /tmp/x ${P}.Trashes/501/'",
            "ssh ember 'mv /tmp/x ${P}.trash'",
            "ssh ember 'mv /tmp/x $P.Trash'",
            "ssh ember 'D=$HOME/.Trash; mv /tmp/x \"$D\"'",
            "ssh ember 'mv /tmp/x \"$D\"'",
            "ssh ember 'mv /tmp/x ${!D}'",
            "ssh ember 'A=mv; \"$A\" /tmp/x \"$D\"'",
            "ssh ember 'alias m=mv; m /tmp/x \"$D\"'",
            "ssh ember 'm() { mv \"$@\"; }; m /tmp/x \"$D\"'",
            "ssh ember 'command mv /tmp/x \"$D\"'",
            "ssh ember 'm\\v /tmp/x ${P}.Trash'",
            'ssh ember "m\'\'v /tmp/x \\${P}.Trash"',
            "ssh ember 'mv /tmp/x $HOME/.Tr${ENDING}ash'",
            "ssh ember 'mv /tmp/x $HOME/\".\"Trash'",
            "ssh ember 'mv /tmp/x $(printf %s \"$HOME/\").Trash'",
            "ssh ember 'mv /tmp/x `printf %s \"$HOME/\"`.Trash'",
            "ssh ember 'echo \"$(mv /tmp/x \"$D\")\"'",
            'ssh ember "sh -c \'P=$HOME/; mv /tmp/x ${P}.Trash\'"',
            "timeout 5 ssh ember 'P=$HOME/; mv /tmp/x ${P}.Trash'",
            "ssh ember 'mv /tmp/x ~/.[Tt]rash'",
            "ssh ember 'mv /tmp/x ~/.*'",
            "ssh ember 'mv /tmp/x ~/{.Trash,.Trash}'",
            'ssh ember \'mv "$SRC" /tmp/archive; mv /tmp/x "$D"\'',
            'ssh ember \'mv "$(mv /tmp/x "$D")" /tmp/archive\'',
            'ssh ember \'mv "$SRC" /tmp/archive > /tmp/out; mv /tmp/x ${P}.Trash\'',
            'ssh ember \'A=m; "$A"v /tmp/x "$D"\'',
            'ssh ember \'A=m; ${A}v /tmp/x "$D"\'',
            'ssh ember \'m{v,v} /tmp/x "$D"\'',
            'ssh ember \'command "$A"v /tmp/x "$D"\'',
            'ssh ember \'env "$A"v /tmp/x "$D"\'',
            'ssh ember \'"$A"v /tmp/x "$D"\'',
            'ssh ember \'m? /tmp/x "$D"\'',
            'ssh ember \'$(printf mv) /tmp/x "$D"\'',
            'ssh ember \'echo "$("$A"v /tmp/x "$D")"\'',
            'ssh ember \'sh -c \'"\'"\'A=m; "$A"v /tmp/x "$D"\'"\'"\'\'',
            'timeout 5 ssh ember \'A=m; "$A"v /tmp/x "$D"\'',
            'ssh linux \'SRC="--target-directory=$HOME/.Tr${X}ash /tmp/x"; mv $SRC /tmp/archive\'',
            'ssh linux \'SRC="--target-directory=$HOME/.Tr${X}ash"; mv "$SRC" /tmp/archive\'',
            'ssh linux \'mv $SRC /tmp/archive\'',
            'ssh linux \'mv "$SRC" /tmp/archive\'',
            'ssh linux \'mv * /tmp/archive\'',
            'ssh linux \'mv {--target-directory=.Trash,/tmp/x} /tmp/archive\'',
            'ssh ember \'CMD=rm; $CMD -rf /remote/valuable-data\'',
            "A=ss; ${A}h ember 'mv /tmp/x ~/.Trash'",
            'A=ss; "$A"h ember \'mv /tmp/x "$D"\'',
            'S=s; s${S}h ember \'mv /tmp/x "$D"\'',
            '"${SSH}" ember \'mv /tmp/x "$D"\'',
            'env ${S}h ember \'mv /tmp/x "$D"\'',
            'command ${S}h ember \'mv /tmp/x "$D"\'',
            's{sh,sh} ember \'mv /tmp/x "$D"\'',
            's?h ember \'mv /tmp/x "$D"\'',
            '"${SSH}" ember "$REMOTE"',
            "sh -c 'A=ss; ${A}h ember \"mv /tmp/x ~/.Trash\"'",
            'timeout 5 ${S}h ember \'mv /tmp/x "$D"\'',
            "sh <<'EOF'\n$CMD ember 'mv /tmp/x \"$D\"'\nEOF",
            "cat <<EOF\n$($CMD ember 'mv /tmp/x \"$D\"')\nEOF",
            '2>/dev/null ${S}h ember \'mv /tmp/x "$D"\'',
            '2>"$OUT" ${S}h ember \'mv /tmp/x "$D"\'',
            'cat <(${S}h ember \'mv /tmp/x "$D"\')',
            'sudo --user worker ${S}h ember \'mv /tmp/x "$D"\'',
            'alias remote="${S}h"; remote ember \'mv /tmp/x "$D"\'',
            "f(){ sh <<'EOF'\n$CMD ember 'mv /tmp/x \"$D\"'\nEOF\n}; f",
            "echo ok # <<EOF\n${S}h ember 'mv /tmp/x \"$D\"'\nEOF",
            "sh <<< 'A=ss; ${A}h ember \"mv /tmp/x ~/.Trash\"'",
            "env sh <<< 'A=ss; ${A}h ember \"mv /tmp/x ~/.Trash\"'",
            "S=s; find /tmp -maxdepth 0 -exec ${S}h ember 'mv /tmp/x ~/.Trash' ';'",
            "S=s; find /tmp -maxdepth 0 -exec env ${S}h ember 'mv /tmp/x ~/.Trash' ';'",
            "S=s; xargs ${S}h ember 'mv /tmp/x ~/.Trash'",
            "shopt -s expand_aliases\nalias remote='env ssh'\nremote ember 'mv /tmp/x ~/.Trash'",
            "shopt -s expand_aliases\nalias remote='timeout 5 ssh'\nremote ember 'mv /tmp/x ~/.Trash'",
            "shopt -s expand_aliases\nalias remote='printf done; env ssh'\nremote ember 'mv /tmp/x ~/.Trash'",
            "S=s; case x in x) ${S}h ember 'mv /tmp/x ~/.Trash';; esac",
            "S=s; coproc ${S}h ember 'mv /tmp/x ~/.Trash'",
            "S=s; function f { ${S}h ember 'mv /tmp/x ~/.Trash'; }; f",
            "source /dev/stdin <<'EOF'\nA=ss; ${A}h ember 'rm -rf /tmp/x'\nEOF",
            ". /dev/stdin <<'EOF'\nA=ss; ${A}h ember 'rm -rf /tmp/x'\nEOF",
            "env bash -c \"source /dev/stdin <<'EOF'\nA=ss; \\${A}h ember 'rm -rf /tmp/x'\nEOF\"",
            "builtin . /dev/fd/0 <<'EOF'\nA=ss; ${A}h ember 'rm -rf /tmp/x'\nEOF",
            """bash <(printf '%s\\n' "A=ss; \\${A}h ember 'rm -rf /tmp/x'")""",
            """env bash <(printf '%s\\n' "A=ss; \\${A}h ember 'rm -rf /tmp/x'")""",
            """source <(printf '%s\\n' "A=ss; \\${A}h ember 'rm -rf /tmp/x'")""",
            """S=s; trap '${S}h ember "rm -rf /tmp/x"' EXIT""",
            """S=s; builtin trap '${S}h ember "rm -rf /tmp/x"' EXIT""",
            """S=s; trap -- '${S}h ember "rm -rf /tmp/x"' EXIT""",
            'trap "$HANDLER" EXIT',
            """printf '%s\\n' "A=ss; \\${A}h ember 'rm -rf /tmp/x'" | bash""",
            """printf '%s\\n' "A=ss; \\${A}h ember 'rm -rf /tmp/x'" | source /dev/stdin""",
            """shopt -s expand_aliases\nalias run='trap'\nS=s; run '${S}h ember "rm -rf /tmp/x"' EXIT""",
            "shopt -s expand_aliases\nalias run='source'\nrun /dev/stdin <<'EOF'\nA=ss; ${A}h ember 'rm -rf /tmp/x'\nEOF",
            "shopt -s expand_aliases\nalias run='env'\nS=s; run ${S}h ember 'rm -rf /tmp/x'",
            "shopt -s expand_aliases\nalias run='printf done;'\nS=s; run ${S}h ember 'rm -rf /tmp/x'",
            "shopt -s expand_aliases\nalias run='xargs'\nS=s; run ${S}h ember 'rm -rf /tmp/x'",
            """bash /dev/fd/3 3<<< 'A=ss; ${A}h ember "rm -rf /tmp/x"'""",
            """3<<< 'A=ss; ${A}h ember "rm -rf /tmp/x"' bash /dev/fd/3""",
            "<<'EOF' bash\nA=ss; ${A}h ember 'rm -rf /tmp/x'\nEOF",
            """< <(printf '%s\\n' "A=ss; \\${A}h ember 'rm -rf /tmp/x'") bash /dev/stdin""",
            "source <(printf s; printf 'sh ember rm -rf /tmp/x')",
            ". <(printf s; printf 'sh ember rm -rf /tmp/x')",
            "bash <(printf s; printf 'sh ember rm -rf /tmp/x')",
            "printf '%s%s' s 'sh ember rm -rf /tmp/x' | bash",
            "s\\\nsh ember 'rm -rf /tmp/x'",
            "ssh ember 'r\\\nm -rf /tmp/x'",
            "ssh ember 'm\\\nv /tmp/x ~/.Trash'",
            "e\\\nnv s\\\nsh ember 'rm -rf /tmp/x'",
            "shopt -s extglob\nss@(h) ember 'rm -rf /tmp/x'",
            "shopt -s extglob\nss+(h) ember 'rm -rf /tmp/x'",
            "shopt -s extglob\ns!(x) ember 'rm -rf /tmp/x'",
            "ssh ember 'D=.Trash; OLDPWD=$HOME/$D; mv /remote/valuable-data rm ~-'",
            "ssh ember 'D=.Trash; PWD=$HOME/$D; mv /remote/valuable-data rm ~+'",
            "ssh ember 'mv /tmp/x ~-'",
            "ssh ember 'mv /tmp/x ~+'",
            "ssh ember 'mv /tmp/x ~-1/subdir'",
            """ssh ember 'SRC="x --target-directory=$HOME/.Tr${X}ash /tmp/y"; mv /tmp/.Trash /tmp/$SRC /tmp/archive'""",
            """ssh ember 'SRC="x --target-directory=$HOME/.Tr${X}ash /tmp/y"; mv /tmp/.Trash "/tmp/"$SRC /tmp/archive'""",
            """ssh ember 'mv /tmp/.Trash "/tmp/${SRC[@]}" /tmp/archive'""",
            """ssh ember 'mv /tmp/.Trash "/tmp/$@" /tmp/archive'""",
        )
        self.grant(path="/tmp/x")
        for command in commands:
            for missing in (False, True):
                with self.subTest(command=command, missing_library=missing):
                    self.decide(command, 2, missing_library=missing)
                    self.assertEqual(len(list(self.notes.glob("*.json"))), 1)
        # A refused dynamic move spends nothing and never looks up a login.
        self.assertEqual(self.calls.read_text().count("-G "), 1)
        self.decide("ssh ember 'mv /tmp/x ~/.Trash'", 0)
        self.assertEqual(list(self.notes.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
