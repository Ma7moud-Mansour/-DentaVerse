import { test as base, expect } from "@playwright/test";
import { execFile } from "node:child_process";
import { promisify } from "node:util";

// Use the normal UI protocol on the isolated test coordinator only. A failed
// sensor journey must not leave a retained pause/modal in the next test.
const reset = `import json,time,uuid
from websockets.sync.client import connect
with connect('ws://127.0.0.1:8001/ws', origin='http://127.0.0.1:5174') as ws:
 state=json.loads(ws.recv())['state']
 for action,payload in [('set_mode',{'mode':'manual'}),('resume',{}),('navigate',{'screen':'studio'})]:
  event=str(uuid.uuid4())
  ws.send(json.dumps(dict(version=1,source='ui',type=action,event_id=event,session_id=state['session']['id'],timestamp=time.time(),payload=payload)))
  while True:
   message=json.loads(ws.recv())
   if message.get('type')=='state':state=message['state']
   if message.get('type')=='error':raise RuntimeError(message)
   if message.get('event_id')==event:
    if message.get('status')!='applied':raise RuntimeError(message)
    break
`;

export const test = base.extend({
  cleanScene: [
    async ({}, use) => {
      await promisify(execFile)(".venv/Scripts/python.exe", ["-c", reset], {
        cwd: "..",
        windowsHide: true,
        timeout: 15000,
      });
      await use();
    },
    { auto: true },
  ],
});
export { expect };
