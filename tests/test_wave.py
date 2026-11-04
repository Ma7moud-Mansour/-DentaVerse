"""Synthetic trajectories exercise DollarPy and auto-wave safety, not human accuracy."""
import copy
import json
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
    h["landmarks"][0].update(x=x,y=y);h["gesture"]=gesture
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
