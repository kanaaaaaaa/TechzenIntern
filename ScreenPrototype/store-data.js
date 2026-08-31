// Shared "backend" stand-in: persists store data to localStorage so
// Add store / Edit changes are reflected across pages without a server.
const StoreDB = (function(){
  const KEY = 'storeLedgerData';
  const SEED = [
    { id:1, name:'Store 1', updated:'8/31', methods:{ emoney:false, qr:true, credit:true, cash:true } },
    { id:3, name:'Store 3', updated:'8/31', methods:{ emoney:false, qr:false, credit:false, cash:true } },
    { id:4, name:'Store 4', updated:'7/29', methods:{ emoney:false, qr:true, credit:false, cash:true } },
  ];

  function todayLabel(){
    const d = new Date();
    return (d.getMonth() + 1) + '/' + d.getDate();
  }

  function save(list){
    try { localStorage.setItem(KEY, JSON.stringify(list)); } catch(e){}
  }

  function load(){
    try {
      const raw = localStorage.getItem(KEY);
      if(raw) return JSON.parse(raw);
    } catch(e){}
    save(SEED);
    return SEED.slice();
  }

  return {
    getAll(){ return load(); },
    get(id){ return load().find(s => String(s.id) === String(id)); },
    add(store){
      const list = load();
      const nextId = list.length ? Math.max(...list.map(s => s.id)) + 1 : 1;
      const newStore = { id: nextId, name: store.name, updated: todayLabel(), methods: store.methods };
      list.push(newStore);
      save(list);
      return newStore;
    },
    update(id, patch){
      const list = load();
      const idx = list.findIndex(s => String(s.id) === String(id));
      if(idx === -1) return null;
      list[idx] = Object.assign({}, list[idx], patch, { updated: todayLabel() });
      save(list);
      return list[idx];
    }
  };
})();
