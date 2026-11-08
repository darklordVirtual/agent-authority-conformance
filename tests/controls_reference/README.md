# Reference subjects for AACP controls

One directory per catalog control, each a minimal subject that exhibits the
weakness the control names, written so the control's probe contract can be
checked end to end without any external project:

```text
<AACP-ID>/weak.py      the subject with the weakness (installed as subject.py)
<AACP-ID>/repair.json  one edit {repair, old, new}; weak + edit = protected subject
<AACP-ID>/probe.py     command probe: exit 0 OBSERVED, 1 NOT_OBSERVED, 3 harness error
```

`tests/test_controls_reference_subjects.py` runs every directory through
`conformance.controls` exactly as a real binding would:

1. weak subject, probe with the repair as its `mutation`: must be `OBSERVED`
   and `DISCRIMINATES`;
2. protected subject (the repair applied), probe with the inverse edit as its
   `sensitivity`: must be `NOT_OBSERVED` and `SENSITIVE`;
3. a broken subject: the probe must exit 3, never 1, so a harness failure is a
   `NON_VERDICT` rather than a protection that held;
4. the report derived from the weak run: `FAIL` on exactly the control's
   property for A-G controls, and never `PASS` anywhere.

A probe exercises a legitimate workflow before the attack and exits 3 if it is
broken. Network probes use runner-owned loopback endpoints and treat what the
endpoint recorded as authoritative over the subject's return value or log.
Canaries carry the `AACP-TEST-CANARY-` prefix.

These are templates, not findings about any project. To bind a real project,
copy the probe's shape (legitimate control, stimulus, observation source,
exit convention) into `templates/controls-binding/` and follow
`docs/CONTROLS.md`. Adding a control to the catalog means adding a directory
here so the contract is shown probe-able, discriminating and sensitive.
