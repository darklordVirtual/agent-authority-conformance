# Control binding template

Copy this directory to `controls/bindings/<project>-<short-rev>/` and follow
[docs/CONTROLS.md](../../docs/CONTROLS.md#binding-a-new-project). Every `UNKNOWN`
and placeholder must be replaced; `python -m unittest tests.test_controls` checks
that committed bindings load and that `expected.json` covers every probe.

For a `command` probe, install probe files into the subject with
`runners.command.install` entries (`from` relative to the binding, `to` relative
to the subject); they are removed after the run.
