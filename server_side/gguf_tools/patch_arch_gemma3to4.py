import struct, sys
# Byte-patch general.architecture value gemma3 -> gemma4 by walking the KV
# header to the exact value offset (NOT a blind global replace). Equal length
# (both 6 bytes), so no offsets shift; tensor data is untouched.
# Idempotent: an already-gemma4 file is a no-op success; failing to find the
# arch KV at all is a hard error.
def patch(path):
    with open(path,'rb') as f: buf=bytearray(f.read())
    assert buf[:4]==b'GGUF', 'not a GGUF file'
    off=4
    struct.unpack_from('<I',buf,off)[0]; off+=4          # version
    struct.unpack_from('<Q',buf,off)[0]; off+=8          # n_tensors
    nkv=struct.unpack_from('<Q',buf,off)[0]; off+=8
    GT_size={0:1,1:1,2:2,3:2,4:4,5:4,6:4,7:1,10:8,11:8,12:8}
    def rd_str(o):
        ln=struct.unpack_from('<Q',buf,o)[0]; o+=8
        return buf[o:o+ln], o+ln
    def skip_val(o,t):
        if t==8:
            ln=struct.unpack_from('<Q',buf,o)[0]; return o+8+ln
        if t==9:
            et=struct.unpack_from('<I',buf,o)[0]; o+=4
            ln=struct.unpack_from('<Q',buf,o)[0]; o+=8
            for _ in range(ln): o=skip_val(o,et)
            return o
        return o+GT_size[t]
    found=False; changed=False
    for _ in range(nkv):
        kb,off=rd_str(off)
        t=struct.unpack_from('<I',buf,off)[0]; off+=4
        if kb==b'general.architecture':
            found=True
            assert t==8, 'arch not string type'
            ln=struct.unpack_from('<Q',buf,off)[0]; voff=off+8
            val=bytes(buf[voff:voff+ln])
            print('  found general.architecture =',val,'at value-offset',voff)
            if val==b'gemma3':
                assert ln==6
                buf[voff:voff+6]=b'gemma4'; changed=True
            elif val==b'gemma4':
                print('  already gemma4 — no change')
            else:
                raise SystemExit(f'  unexpected arch {val!r} — refusing to patch')
            off=voff+ln
        else:
            off=skip_val(off,t)
    assert found, 'general.architecture KV not found'
    if changed:
        with open(path,'wb') as f: f.write(buf)
        print('  patched gemma3->gemma4 OK:',path)
    else:
        print('  no write needed:',path)

if __name__=='__main__':
    for p in sys.argv[1:]:
        print('###',p); patch(p)
