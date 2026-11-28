
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const extension = 'chrome-extension://mmlmfjhmonkocbjadbfplnigmagldckm/connect.html';
const name = 'EP birth fixture [12345678]';
const url = extension + '?client=' + encodeURIComponent(JSON.stringify({name}));
async function run(stop, change) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'birth-fixture-'));
  const birth = {token:'a'.repeat(32), path:path.join(dir,'birth.json'),
    job_id:'b'.repeat(32), client_name:name, generation:{pid:1,started:'fixture'},
    connectorId:1, sourceWindowId:5, marker:'about:blank#ep-isolation-'+'a'.repeat(32)};
  const tabs = new Map([[1,{id:1,windowId:5,groupId:7,url}],
    [99,{id:99,windowId:5,groupId:9,url:'https://peer.example/'}]]);
  const windows = new Set([5]);
  const removals = [];
  let stage, fail=true, recovery=false, closeInterrupted=false;
  const remove = async ids => {
    for (const id of [ids].flat()) {
      removals.push(id); const t=tabs.get(id);tabs.delete(id);
      if(t&&![...tabs.values()].some(x=>x.windowId===t.windowId)) windows.delete(t.windowId);
      if(recovery && change==='partialClose' && !closeInterrupted){
        closeInterrupted=true;throw Error('transport lost after one removal');
      }
    }
    if(stop==='remove'&&fail) {fail=false;throw Error('vendor_target_closed');}
  };
  const connector={context:()=>({pages:()=>[connector]}),evaluate:async(fn,arg)=>fn(arg)};
  global.chrome={
    tabs:{
      getCurrent:async()=>tabs.get(1),
      get:async id=>{if(!tabs.has(id))throw Error('missing');return tabs.get(id);},
      query:async q=>[...tabs.values()].filter(t=>
        (q.windowId===undefined||t.windowId===q.windowId)&&
        (q.groupId===undefined||t.groupId===q.groupId)),
      remove
    },
    windows:{
      getAll:async()=>[...windows].map(id=>({id})),
      create:async ({url})=>{
        stage=JSON.parse(fs.readFileSync(birth.path)).stage;
        assert.equal(stage,'creating');
        assert.equal(url,birth.marker,'birth marker must predate the Chrome side effect');
        const seed={id:2,windowId:6,groupId:-1,url:'',pendingUrl:url};
        tabs.set(2,seed);windows.add(6);
        if(stop==='create'&&fail){fail=false;throw Error('vendor_target_closed');}
        return {id:6,tabs:[seed]};
      },
      remove:async()=>{throw Error('never close an unverified whole window');}
    },
    tabGroups:{
      get:async()=>({title:'fixture'}),
      move:async(id,{windowId})=>{
        assert.equal(JSON.parse(fs.readFileSync(birth.path)).stage,'created');
        tabs.get(1).windowId=windowId;
        if(stop==='move'&&fail){fail=false;throw Error('vendor_target_closed');}
      }
    },
    runtime:{sendMessage:async()=>({sessions:change==='claimed'?
      [{clientName:'peer',tabIds:[2]}]:[]})},
    debugger:{getTargets:async()=>change==='attached'?[{tabId:2,attached:true}]:[]}
  };
  try {
    await assert.rejects(()=>newOwnedState(connector,birth),/vendor_target_closed/);
    const journal=JSON.parse(fs.readFileSync(birth.path));
    assert.equal(journal.token,birth.token);
    if(stop==='move'||stop==='remove')assert.equal(journal.windowId,6);
    if(change==='navigated'){tabs.get(2).url='https://human.example/';delete tabs.get(2).pendingUrl;}
    if(change==='transferred')tabs.get(2).windowId=5;
    if(change==='foreign')tabs.set(88,{id:88,windowId:6,groupId:12,url:'https://human.example/'});
    const args={...journal,client_name:name,connectorOrigin:extension};
    const peer=JSON.stringify(tabs.get(99));
    const snapshot=await reconcileIsolationBirth(connector,args);
    if(['claimed','attached','navigated','transferred'].includes(change)){
      assert.equal(snapshot.held,true);assert.deepEqual(removals,[]);
      return;
    }
    const beforeRecovery=[...removals];
    args.cleanup={tabIds:snapshot.ids,windowId:snapshot.windowId};
    recovery=true;
    let outcome=await reconcileIsolationBirth(connector,{...args,remove:true,expected:snapshot.proof});
    if(change==='partialClose'){
      assert.equal(outcome.held,true);
      const remaining=await reconcileIsolationBirth(connector,args);
      outcome=await reconcileIsolationBirth(connector,{...args,remove:true,expected:remaining.proof});
    }
    assert.equal(outcome.closed,true);
    assert.equal(JSON.stringify(tabs.get(99)),peer);
    assert.equal(tabs.has(1),false);
    assert.equal(tabs.has(2),false);
    assert.equal(windows.has(5),true,'original peer window must survive');
    assert.equal(windows.has(6),change==='foreign');
    if(change==='foreign')assert.equal(tabs.has(88),true);
    assert.deepEqual([...new Set([...beforeRecovery,...removals])].sort(),[1,2]);
    // A vanished seed after our recorded removal is proof of completion, not
    // a new creation retry. Repeat even when the first response was lost.
    const again=await reconcileIsolationBirth(connector,args);
    const repeated=await reconcileIsolationBirth(connector,{...args,remove:true,expected:again.proof});
    assert.equal(repeated.closed,true);
  } finally {fs.rmSync(dir,{recursive:true,force:true});}
}
(async()=>{
  let cases=0;
  for(const stop of ['create','move','remove']){
    await run(stop);cases++;
    await run(stop,'foreign');cases++;
  }
  for(const change of ['claimed','attached','navigated','transferred']){
    await run('move',change);cases++;
  }
  await run('create','claimed');cases++;
  await run('create','navigated');cases++;
  await run('create','partialClose');cases++;
  await run('move','partialClose');cases++;
  console.log(JSON.stringify({cases}));
})().catch(e=>{console.error(e);process.exitCode=1;});
