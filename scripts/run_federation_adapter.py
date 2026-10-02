"""CLI for deterministic, read-only federation adapter resolution."""
import argparse
from conformance.adapter import write_bundle

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--manifest",required=True)
    p.add_argument("--subject-root",required=True)
    p.add_argument("--out",required=True)
    a=p.parse_args()
    write_bundle(a.manifest,a.subject_root,a.out)

if __name__=="__main__":
    main()
