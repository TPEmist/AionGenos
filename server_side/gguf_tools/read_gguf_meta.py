import sys, struct
def read_gguf(path):
    with open(path,'rb') as f:
        magic=f.read(4)
        if magic!=b'GGUF': return {'err':'not gguf','magic':magic}
        ver=struct.unpack('<I',f.read(4))[0]
        n_tensors=struct.unpack('<Q',f.read(8))[0]
        n_kv=struct.unpack('<Q',f.read(8))[0]
        def rd_str():
            ln=struct.unpack('<Q',f.read(8))[0]; return f.read(ln).decode('utf-8','replace')
        GT={0:'<B',1:'<b',2:'<H',3:'<h',4:'<I',5:'<i',6:'<f',7:'<?',8:'str',9:'arr',10:'<Q',11:'<q',12:'<d'}
        def rd_val(t):
            if t==8: return rd_str()
            if t==9:
                et=struct.unpack('<I',f.read(4))[0]; ln=struct.unpack('<Q',f.read(8))[0]
                return [rd_val(et) for _ in range(ln)]
            fmt=GT[t]; sz=struct.calcsize(fmt); return struct.unpack(fmt,f.read(sz))[0]
        kv={}
        for _ in range(n_kv):
            k=rd_str(); t=struct.unpack('<I',f.read(4))[0]; kv[k]=rd_val(t)
        # tensor infos
        tinfo=[]
        for _ in range(n_tensors):
            name=rd_str(); ndim=struct.unpack('<I',f.read(4))[0]
            dims=[struct.unpack('<Q',f.read(8))[0] for _ in range(ndim)]
            typ=struct.unpack('<I',f.read(4))[0]; off=struct.unpack('<Q',f.read(8))[0]
            tinfo.append((name,dims))
        return {'ver':ver,'n_tensors':n_tensors,'arch':kv.get('general.architecture'),
                'type':kv.get('general.type'),'tinfo':tinfo}
for p in sys.argv[1:]:
    r=read_gguf(p)
    print(f"\n### {p}")
    if 'err' in r: print("  ",r); continue
    print(f"  arch={r['arch']}  type={r['type']}  n_tensors={r['n_tensors']}")
    for name,dims in r['tinfo'][:6]:
        print(f"    {name}  dims={dims}")
