"""Aggregate actual consented anonymous survey CSVs; never fabricate responses."""
import argparse
import csv
import re
from collections import Counter
from pathlib import Path

CHOICES = {
    "role": ("student", "demonstrator", "other"),
    "study_year": tuple(str(n) for n in range(1,9)),
    "digital_tools_frequency": ("never", "rarely", "sometimes", "often", "very_often"),
    "gesture_experience": ("yes", "no", "unsure"),
    "useful_activities": ("identify", "rotate", "layers", "instrument", "progress", "notes"),
    "device": ("laptop", "desktop", "tablet", "other"),
    "setting": ("alone", "classroom", "laboratory", "other"),
    "barriers": ("instructions", "camera", "accidental_gestures", "small_controls", "visual_complexity", "discomfort", "privacy", "other"),
    "recovery_preferences": ("explanation", "fix_steps", "undo_reset", "pause_resume", "help"),
    "persistent_information": ("number", "name", "tool", "mode", "instructions", "progress"),
    **{k: tuple(str(n) for n in range(1,6)) for k in ("fdi_confidence", "manual_controls_importance", "camera_comfort")},
}
MULTI = {"useful_activities", "setting", "barriers", "recovery_preferences", "persistent_information"}


def load_responses(paths):
    rows, seen = [], set()
    for path in paths:
        with Path(path).open(encoding="utf-8-sig",newline="") as stream:
            reader=csv.DictReader(stream)
            if not reader.fieldnames or not {"anonymous_code","consented"}.issubset(reader.fieldnames):
                raise ValueError("CSV must have anonymous_code and consented columns")
            for line,raw in enumerate(reader,2):
                if not any(raw.values()): continue
                code=(raw.get("anonymous_code") or "").strip()
                if not re.fullmatch(r"[A-Za-z0-9_-]{1,32}",code):
                    raise ValueError(f"Row {line}: invalid anonymous code")
                if code in seen: raise ValueError(f"Row {line}: duplicate anonymous code; resolve before analysis")
                if raw.get("consented","").strip().lower() != "yes":
                    raise ValueError(f"Row {line}: explicit consent is missing")
                row={"anonymous_code":code}
                for field,options in CHOICES.items():
                    value=(raw.get(field) or "").strip()
                    values=value.split(";") if field in MULTI and value else [value] if value else []
                    if any(v not in options for v in values):
                        raise ValueError(f"Row {line}: invalid value for {field}")
                    row[field]=sorted(set(values))
                # Free text can identify someone: count it, but never echo it to the report.
                row["has_comment"]=bool((raw.get("open_comment") or "").strip())
                rows.append(row);seen.add(code)
    if not rows:raise ValueError("No actual responses supplied; no results report was generated")
    return rows


def report(rows):
    lines=["# DentaVerse survey aggregation", "", f"Actual submitted rows: {len(rows)}. These are self-reported preferences, not observed learning gains.", "",
        "Each denominator includes only respondents answering that field. Multiple selections can total more than 100%. Missing responses are not zeros.", "",
        "| Field | Answering | Missing | Counts (percent of answering) |", "|---|---:|---:|---|"]
    for field,options in CHOICES.items():
        answered=[r[field] for r in rows if r[field]]
        counts=Counter(v for values in answered for v in values)
        distribution="; ".join(f"{v}: {counts[v]} ({counts[v]/len(answered)*100:.1f}%)" for v in options) if answered else "No answers"
        lines.append(f"| {field} | {len(answered)} | {len(rows)-len(answered)} | {distribution} |")
    lines += ["",f"Non-empty free-text comments: {sum(r['has_comment'] for r in rows)}. Comments are not reproduced; review and de-identify them privately before manual theme coding.","",
        "## Critical analysis still required", "", "Document recruitment, actual dental roles, consent/retention, exclusions and convenience-sample limitations. Do not infer causation, clinical competence or population-level effects from these counts.","",
        "Review the anonymous comments for themes and counterexamples. Link each proposed change to actual evidence and recheck it with participants. Document the prototype commit and whether each observed trial used real sensors or manual input.","",
        "| Evidence / theme | Design decision | Implemented change | Recheck |", "|---|---|---|---|", "| To complete from actual findings | | | |", ""]
    return "\n".join(lines)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("responses",nargs="+",type=Path)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    try: text=report(load_responses(args.responses))
    except (OSError,ValueError) as exc:parser.exit(2,f"Cannot analyze: {exc}\n")
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(text,encoding="utf-8")
    print(f"Saved aggregate report: {args.output}. Manual critical analysis is still required.")


if __name__ == "__main__":main()
