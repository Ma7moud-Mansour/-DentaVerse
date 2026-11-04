"""Synthetic trajectories exercise DollarPy and auto-wave safety, not human accuracy."""
import copy
import json
import math
import time
from pathlib import Path
from unittest.mock import Mock

import pytest
from backend.engine import Engine
from backend.protocol import Message
from backend.storage import Store
from backend.wave import RightWave

OPEN=json.loads((Path(__file__).parent/"fixtures/hand-signals-synthetic.json").read_text(encoding="utf-8"))["open"]


def palm(x=.5,y=.5,side="right",gesture="open_palm"):
    h=copy.deepcopy(next(h for h in OPEN if h["id"]==side))
    dx,dy=x-h["landmarks"][0]["x"],y-h["landmarks"][0]["y"]
    for point in h["landmarks"]:point.update(x=point["x"]+dx,y=point["y"]+dy)
    h["center"]={axis:sum(h["landmarks"][i][axis] for i in (0,5,9,13,17))/5 for axis in ("x","y")}
    h["gesture"]=gesture
    return h


def perform(wave,start=0,context=("session",1),side="right",gesture="open_palm",dt=.1):
    matches=[]
    for i in range(5):wave.update([palm(side=side,gesture=gesture)],start+i*dt,context)
    for i,x in enumerate((.5,.4,.3,.4,.5,.6,.7,.6,.5,.4,.3,.4,.5)):
        match=wave.update([palm(x,side=side,gesture=gesture)],start+(i+5)*dt,context)
        if match:matches.append(match)
    return matches


def test_actual_dollarpy_recognizes_one_wave_at_low_camera_rate():
    wave=RightWave();wave.recognizer.recognize=Mock(wraps=wave.recognizer.recognize)
    matches=perform(wave,dt=.125)
    assert len(matches)==1 and matches[0]["name"]=="wave"
    assert matches[0]["method"]=="DollarPy" and matches[0]["template_origin"]=="authored_reference"
    assert matches[0]["score"]>=RightWave.THRESHOLD
    wave.recognizer.recognize.assert_called()


@pytest.mark.parametrize("side,gesture",[("left","open_palm"),("right","fist"),("right","pinch")])
def test_other_hand_or_closed_pose_never_cycles(side,gesture):
    assert not perform(RightWave(),side=side,gesture=gesture)


def test_single_sweep_stationary_and_vertical_are_not_waves():
    for path in ([.5]*20,[.2+i*.02 for i in range(20)]):
        wave=RightWave()
        assert not any(wave.update([palm(x)],i*.1,("s",1)) for i,x in enumerate(path))
    wave=RightWave()
    assert not any(wave.update([palm(.5,.2+(i%5)*.1)],i*.1,("s",1)) for i in range(30))


def test_context_changes_cannot_replay_latched_wave_and_quiet_rearms():
    wave=RightWave();assert len(perform(wave))==1
    assert not perform(wave,start=2,context=("session",2))
    for i in range(12):wave.update([palm()],4+i*.1,("session",2))
    assert len(perform(wave,start=5.3,context=("session",2)))==1


def send(engine,kind,payload=None,source="ui"):
    return engine.apply(Message(source=source,type=kind,session_id=engine.state["session"]["id"],payload=payload or {}))


def preview(engine,hands=None):
    send(engine,"POSE_FRAME",{"landmarks":[],"hands":[palm()] if hands is None else hands,"hand_tracking":True,"control_epoch":engine.state["session"]["gesture_epoch"]},"vision")


@pytest.fixture
def engine():
    store=Store(":memory:");e=Engine(store)
    send(e,"select_tooth",{"tooth":16});send(e,"isolate")
    e.worker_status("vision",True);preview(e);send(e,"set_mode",{"mode":"hand"});preview(e)
    yield e
    store.close()


def match(engine):
    return {"name":"wave","score":.99,"method":"DollarPy","template_origin":"authored_reference","epoch":engine.state["session"]["gesture_epoch"]}


def test_server_wave_cycles_tools_once_and_keeps_transforms(engine,monkeypatch):
    now=time.monotonic()
    initial=copy.deepcopy(engine.state["session"])
    event=Message(source="vision",type="GESTURE_RECOGNIZED",session_id=initial["id"],payload=match(engine))
    assert engine.apply(event)["status"]=="applied"
    assert engine.state["session"]["tool"]=="mirror"
    assert engine.apply(event)["status"]=="duplicate"
    with pytest.raises(ValueError):send(engine,"GESTURE_RECOGNIZED",match(engine),"vision")
    for index,tool in enumerate(("explorer","hand"),1):
        monkeypatch.setattr("backend.engine.time.monotonic",lambda index=index:now+index*2)
        preview(engine);send(engine,"GESTURE_RECOGNIZED",match(engine),"vision")
        assert engine.state["session"]["tool"]==tool
    assert engine.state["session"]["rotation"]==initial["rotation"]
    assert engine.state["session"]["tool_position"]==initial["tool_position"]
    assert engine.state["last_gesture"]["name"]=="wave"


@pytest.mark.parametrize("kind,payload",[("pause",{}),("navigate",{"screen":"review"}),("set_mode",{"mode":"manual"}),("wave_enabled",{"enabled":False})])
def test_wave_blocked_outside_explicit_active_hand_workbench(engine,kind,payload):
    send(engine,kind,payload)
    with pytest.raises(ValueError):send(engine,"GESTURE_RECOGNIZED",match(engine),"vision")
    assert engine.state["session"]["tool"]=="hand"


def test_wave_requires_open_right_fresh_preview_epoch_and_matching_score(engine):
    p=match(engine);p["score"]=.4
    with pytest.raises(ValueError):send(engine,"GESTURE_RECOGNIZED",p,"vision")
    preview(engine,[palm(side="left")])
    with pytest.raises(ValueError):send(engine,"GESTURE_RECOGNIZED",match(engine),"vision")
    preview(engine);p=match(engine);p["epoch"]-=1
    with pytest.raises(ValueError):send(engine,"GESTURE_RECOGNIZED",p,"vision")


def test_active_tool_toggle_removes_it_and_persists_settings(engine):
    send(engine,"toggle_tool",{"tool":"mirror"});assert engine.state["session"]["tool"]=="mirror"
    send(engine,"toggle_tool",{"tool":"mirror"});assert engine.state["session"]["tool"]=="hand"
    send(engine,"wave_enabled",{"enabled":False});assert not Engine(engine.store).state["session"]["wave_enabled"]


@pytest.mark.parametrize("style", ["bent_finger", "sloped", "curved", "small", "pivot", "dropped_frame"])
def test_natural_palm_paths_reach_actual_dollarpy(style):
    wave=RightWave();matches=[]
    path=(.5,.4,.3,.4,.5,.6,.7,.6,.5,.4,.3,.4,.5)
    for i in range(5):wave.update([palm()],i*.125,("s",1))
    for i,x in enumerate(path):
        if style=="small":x=.5+(x-.5)*.3
        y=.5+(.2*(x-.5) if style=="sloped" else .018*math.sin(i*.7) if style=="curved" else 0)
        h=palm(x,y)
        if style=="bent_finger":
            h["gesture"]="neutral";h["fingers"]["ring"]=False;h["extended_fingers"]=sum(h["fingers"].values())
        if style=="pivot":h["landmarks"][0].update(x=.5,y=.5)
        value=wave.update([] if style=="dropped_frame" and i==4 else [h],(i+5)*.125,("s",1))
        if value:matches.append(value)
    assert len(matches)==1
    assert matches[0]["method"]=="DollarPy"


def test_jitter_circle_and_immediate_pinch_are_not_waves():
    for path in [[(.5+.008*math.sin(i),.5) for i in range(25)],
                 [(.5+.15*math.cos(i*.4),.5+.15*math.sin(i*.4)) for i in range(25)]]:
        wave=RightWave()
        assert not any(wave.update([palm(x,y)],i*.1,("s",1)) for i,(x,y) in enumerate(path))
    wave=RightWave()
    for i in range(8):wave.update([palm(.5-i*.02)],i*.1,("s",1))
    h=palm();h["pinch_ratio"]=.3  # Debounced label can still say open.
    assert wave.update([h],.8,("s",1)) is None
    assert wave.samples==[] and wave.feedback["phase"]=="open"


def test_templates_do_not_grow_across_dollarpy_attempts():
    wave=RightWave();counts=[len(points) for _,points in wave.references]
    for i in range(3):
        wave.latched=False;wave.last_fire=-math.inf;wave.clear()
        assert perform(wave,start=i*4)
    assert [len(points) for _,points in wave.references]==counts


def test_server_accepts_same_naturally_open_palm_as_worker(engine):
    h=palm(gesture="neutral");h["fingers"]["ring"]=False;h["extended_fingers"]=sum(h["fingers"].values())
    preview(engine,[h]);send(engine,"GESTURE_RECOGNIZED",match(engine),"vision")
    assert engine.state["session"]["tool"]=="mirror"


def test_wave_feedback_is_bounded_and_not_saved(engine):
    payload={"landmarks":[],"hands":[palm()],"hand_tracking":True,"control_epoch":engine.state["session"]["gesture_epoch"],"wave":{"phase":"tracking","turns":1}}
    send(engine,"POSE_FRAME",payload,"vision")
    assert engine.snapshot()["vision"]["pose"]["wave"]=={"phase":"tracking","turns":1}
    for bad in ({"phase":"unknown","turns":0},{"phase":"tracking","turns":50},{"phase":"ready","turns":True}):
        with pytest.raises(ValueError):send(engine,"POSE_FRAME",{**payload,"wave":bad},"vision")
    saved=engine.store.load_workspace()
    assert "pose" not in saved and "wave" not in saved["session"]
