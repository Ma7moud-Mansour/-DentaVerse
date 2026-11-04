"""Artificial CSV rows verify aggregation; never participant research evidence."""
import csv
import pytest
from tools.analyze_survey import load_responses,report


def write(path,rows):
    with path.open("w",encoding="utf-8-sig",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=["anonymous_code","consented","role","fdi_confidence","useful_activities","open_comment"])
        writer.writeheader();writer.writerows(rows)


def test_denominators_multiselect_and_private_free_text(tmp_path):
    p=tmp_path/"synthetic.csv"
    write(p,[{"anonymous_code":"synthetic1","consented":"yes","role":"student","fdi_confidence":"5","useful_activities":"rotate;layers;rotate","open_comment":"PRIVATE TEXT"},
        {"anonymous_code":"synthetic2","consented":"yes","role":"student","useful_activities":"layers"}])
    text=report(load_responses([p]))
    assert "| fdi_confidence | 1 | 1 |" in text
    assert "rotate: 1 (50.0%)" in text and "layers: 2 (100.0%)" in text
    assert "PRIVATE TEXT" not in text and "Non-empty free-text comments: 1" in text


@pytest.mark.parametrize("change",[{"consented":"no"},{"fdi_confidence":"0"},{"role":"identifying personal text"}])
def test_rejects_nonconsent_and_invalid_fields(tmp_path,change):
    p=tmp_path/"synthetic.csv";write(p,[{"anonymous_code":"synthetic","consented":"yes",**change}])
    with pytest.raises(ValueError):load_responses([p])


def test_empty_and_duplicate_files_never_produce_counts(tmp_path):
    p=tmp_path/"synthetic.csv";write(p,[])
    with pytest.raises(ValueError,match="No actual"):load_responses([p])
    write(p,[{"anonymous_code":"synthetic","consented":"yes"}])
    with pytest.raises(ValueError,match="duplicate"):load_responses([p,p])
