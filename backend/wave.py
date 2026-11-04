"""Automatic right-open-palm wave segmentation and genuine DollarPy matching.

Reference shapes below are authored geometry, never claimed to be human captures.
Temporal gates supplement $P, which intentionally discards stroke order.
"""
import math
from dollarpy import Point, Recognizer, Template


def reference(points, steps=12):
    result=[]
    for a,b in zip(points,points[1:]):
        result.extend(Point(a[0]+(b[0]-a[0])*i/steps,a[1]+(b[1]-a[1])*i/steps,1) for i in range(steps))
    result.append(Point(*points[-1],1))
    return result


class RightWave:
    THRESHOLD=.82
    COOLDOWN=1.8

    def __init__(self):
        circle=[(.5+.4*math.cos(i*math.tau/32),.5+.4*math.sin(i*math.tau/32)) for i in range(33)]
        self.recognizer=Recognizer([
            Template("wave",reference([(.2,.5),(.8,.5),(.2,.5),(.8,.5)])),
            Template("vertical",reference([(.5,.2),(.5,.8),(.5,.2),(.5,.8)])),
            Template("circle",[Point(x,y,1) for x,y in circle]),
            Template("V",reference([(.2,.2),(.5,.8),(.8,.2)])),
        ])
        self.context=None
        self.last_fire=-math.inf
        self.latched=False
        self.quiet_since=None
        self.clear()

    def clear(self):
        self.samples=[]
        self.previous=None
        self.open_since=None
        self.direction=0
        self.turns=0
        self.extreme=None

    def update(self,hands,now,context,enabled=True):
        if context!=self.context:
            self.context=context;self.clear()
        hand=next((h for h in hands if h["id"]=="right"),None)
        opened=hand and hand["in_frame"] and hand["gesture"]=="open_palm" and hand["extended_fingers"]>=4 and hand["pinch_ratio"]>.6
        if not enabled or not opened:
            self.clear();self.quiet_since=None
            return None
        point=hand["landmarks"][0]
        x,y=point["x"],point["y"]
        if not all(math.isfinite(v) for v in (x,y,now)):return None
        if self.open_since is None:self.open_since=now
        previous=self.previous
        self.previous=(now,x,y)
        if not previous:return None
        dt=now-previous[0]
        if dt<=0 or dt>.4:
            self.clear();return None
        dx=x-previous[1]
        speed=math.dist((x,y),previous[1:])/dt
        if speed<.12:
            if self.quiet_since is None:self.quiet_since=now
            if now-self.quiet_since>=.5 and now-self.last_fire>=self.COOLDOWN:
                self.latched=False
        else:self.quiet_since=None
        if self.latched or now-self.last_fire<self.COOLDOWN or now-self.open_since<.18:return None
        if not self.samples:
            if abs(dx)/dt<.3:return None
            self.samples=[previous]
            self.direction=1 if dx>0 else -1
            self.turns=0;self.extreme=previous[1]
        self.samples.append((now,x,y))
        if self.direction>0:
            self.extreme=max(self.extreme,x)
            if x<self.extreme-.045:self.turns+=1;self.direction=-1;self.extreme=x
        else:
            self.extreme=min(self.extreme,x)
            if x>self.extreme+.045:self.turns+=1;self.direction=1;self.extreme=x
        elapsed=now-self.samples[0][0]
        if elapsed>1.6:
            self.samples=[];return None
        if len(self.samples)<6 or self.turns<2 or elapsed<.25:return None
        xs=[p[1] for p in self.samples];ys=[p[2] for p in self.samples]
        width,height=max(xs)-min(xs),max(ys)-min(ys)
        if width<.14 or height>max(.10,width*.55):return None
        clean=[]
        for _,px,py in self.samples:
            if not clean or math.dist((px,py),clean[-1])>1e-6:clean.append((px,py))
        if len(clean)<5:return None
        name,score=self.recognizer.recognize([Point(px,py,1) for px,py in clean])
        score=max(0,min(1,float(score)))
        if name!="wave" or score<self.THRESHOLD:return None
        self.last_fire=now;self.latched=True;self.samples=[]
        return {"name":"wave","score":score,"method":"DollarPy","template_origin":"authored_reference"}
