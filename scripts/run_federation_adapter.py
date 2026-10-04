"""CLI for deterministic, read-only federation adapter resolution."""
import argparse
import json
import platform
import shlex
import subprocess
import sys
from pathlib import Path
from conformance.adapter import (
    AdapterError, canonical_json, load_manifest, resolve, sha256_bytes, write_run_package,
)

ROOT = Path(__file__).resolve().parents[1]

def git_output(root, *arguments):
    return subprocess.run(["git", "-C", str(root), *arguments],
                          capture_output=True, text=True, check=True).stdout.strip()

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--manifest",required=True)
    p.add_argument("--subject-root",required=True)
    output = p.add_mutually_exclusive_group(required=True)
    output.add_argument("--out")
    output.add_argument("--record-dir")
    p.add_argument("--runner")
    p.add_argument("--fixture-author")
    p.add_argument("--classification", choices=["AUTHOR_RUN", "REPRODUCTION"], default="AUTHOR_RUN")
    p.add_argument("--summary", help="Write a publication-gated Markdown CI summary")
    a=p.parse_args()
    if a.record_dir and (not a.runner or not a.fixture_author):
        p.error("--record-dir requires --runner and --fixture-author")
    if a.summary and not a.record_dir:
        p.error("--summary requires --record-dir")
    manifest = load_manifest(a.manifest)
    subject_revision = None
    if a.record_dir:
        subject_revision = git_output(a.subject_root, "rev-parse", "HEAD")
        if subject_revision.lower() != manifest["subject"]["revision"].lower():
            raise AdapterError("subject checkout HEAD differs from the frozen subject revision")
    bundle = resolve(manifest, a.subject_root)
    if a.out:
        Path(a.out).write_bytes(canonical_json(bundle))
    else:
        procedure_files = ["conformance/adapter.py", "conformance/validation.py",
                           "scripts/run_federation_adapter.py",
                           "schema/federation-run-v1.schema.json",
                           "schema/federation-evidence-bundle-v1.schema.json"]
        dirty = bool(git_output(ROOT, "status", "--porcelain", "--untracked-files=no"))
        record = write_run_package(
            manifest, bundle, a.record_dir,
            revision=git_output(ROOT, "rev-parse", "HEAD"), runner=a.runner,
            fixture_author=a.fixture_author, classification=a.classification,
            command=shlex.join([sys.executable, "-m", "scripts.run_federation_adapter", *sys.argv[1:]]),
            environment={
                "python": platform.python_version(), "platform": platform.platform(),
                "consumer_worktree_dirty": dirty,
                "declared_adapter_revision": manifest["adapter"]["revision"],
                "input_manifest_raw_sha256": sha256_bytes(Path(a.manifest).read_bytes()),
                "subject_checkout_revision": subject_revision,
                "procedure_files_sha256": {
                    name: sha256_bytes((ROOT / name).read_bytes()) for name in procedure_files
                },
            },
        )
        if a.summary:
            public = bundle["publication_authorized"] and not dirty
            text = "# Federation resolution\n\n"
            text += "Resolution only; no property verdict, endorsement or independence credit.\n\n"
            text += f"Publication policy: `{bundle['review_policy']['mode']}`.\n\n"
            text += f"Run commitment: `{record['run_id']}`.\n\n"
            text += f"SHA256SUMS SHA-256: `{sha256_bytes((Path(a.record_dir) / 'SHA256SUMS').read_bytes())}`.\n\n"
            if public:
                text += f"Adapter status: `{bundle['adapter_status']}`.\n\n"
                text += "| Artifact ID (JSON) | Resolution |\n|---|---|\n"
                for evidence in bundle["evidence"]:
                    identifier = json.dumps(evidence["artifact_id"], ensure_ascii=True)
                    identifier = identifier.replace("|", "\\u007c").replace("`", "\\u0060").replace("<", "\\u003c")
                    text += f"| `{identifier}` | `{evidence['resolution']}` |\n"
            else:
                text += "Result details and downloadable evidence withheld: review/consent or a clean committed procedure is required.\n"
            Path(a.summary).write_text(text, encoding="utf-8")
    return 0 if bundle["adapter_status"] == "RESOLVED" else 1

if __name__=="__main__":
    raise SystemExit(main())
