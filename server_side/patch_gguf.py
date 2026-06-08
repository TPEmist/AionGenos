import sys
from pathlib import Path

# Add gguf-py to path
sys.path.insert(1, str(Path.home() / "CYTu/llama.cpp/gguf-py"))
import gguf

def main():
    if len(sys.argv) < 2:
        print("Usage: python patch_gguf.py <adapter.gguf>")
        sys.exit(1)
        
    adapter_path = Path(sys.argv[1])
    if not adapter_path.exists():
        print(f"Error: file not found: {adapter_path}")
        sys.exit(1)
        
    print(f"Reading: {adapter_path}")
    reader = gguf.GGUFReader(adapter_path)
    
    # Read fields
    fields = {}
    for key, field in reader.fields.items():
        # skip architecture because we will override it
        if key == "general.architecture":
            continue
        fields[key] = field
        
    # Prepare writer
    output_path = adapter_path.with_suffix(".tmp.gguf")
    writer = gguf.GGUFWriter(output_path, arch="gemma4")
    
    # Copy all other fields
    for key, field in reader.fields.items():
        if key == "general.architecture":
            continue
        # We need to add the field with its appropriate type
        val = field.parts[-1]
        # Decode bytes/numpy types if necessary
        if field.types and field.types[0] == gguf.GGUFValueType.STRING:
            # val is a numpy array of bytes or string
            val_str = bytes(val).decode('utf-8')
            writer.add_string(key, val_str)
        elif field.types and field.types[0] == gguf.GGUFValueType.FLOAT32:
            writer.add_float32(key, float(val[0]))
        elif field.types and field.types[0] == gguf.GGUFValueType.UINT32:
            writer.add_uint32(key, int(val[0]))
        elif field.types and field.types[0] == gguf.GGUFValueType.INT32:
            writer.add_int32(key, int(val[0]))
        else:
            # Fallback
            try:
                writer.add_val(key, val)
            except Exception:
                pass
                
    # Copy all tensors
    for tensor in reader.tensors:
        print(f"Copying tensor: {tensor.name} (shape: {tensor.shape}, type: {tensor.tensor_type})")
        writer.add_tensor(tensor.name, tensor.data, raw_shape=tensor.shape)
        
    print("Writing new GGUF file...")
    writer.write_header_to_file()
    writer.write_kv_data_to_file()
    writer.write_tensors_to_file()
    writer.close()
    
    # Replace original
    output_path.replace(adapter_path)
    print("GGUF architecture successfully patched to 'gemma4'!")

if __name__ == "__main__":
    main()
