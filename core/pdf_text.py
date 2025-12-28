import fitz  # PyMuPDF
from typing import Union

def extract_text_from_bytes(file_bytes: bytes) -> str:
    doc = fitz.open(stream=file_bytes)
    chunks = []
    for page in doc:
        chunks.append(page.get_text())
    doc.close()
    # return "\n".join(chunks)
    text = "\n".join(chunks)
    
    # 🔥 ADD THESE 3 LINES ONLY (safe truncation)
    if len(text) > 4000:
        text = text[:4000] + "\n\n[Resume truncated for parsing]"
    
    return text

def extract_text_from_path(path: str) -> str:
    doc = fitz.open(path)
    chunks = []
    for page in doc:
        chunks.append(page.get_text())
    doc.close()
    return "\n".join(chunks)


if __name__ == "__main__":
    
    test_pdf = r"C:\Users\Admin\Desktop\mybyte\GroqResumeParser\data\test_resumes\Abhishek Uniyal Resume.pdf"  
    
    print(f"🔍 Testing PDF extraction on: {test_pdf}")
    print("-" * 50)
    
    try:
        # Test path-based extraction (most common)
        text = extract_text_from_path(test_pdf)
        print("✅ Path extraction SUCCESS!")
        print(f"📄 Total chars: {len(text)}")
        print(f"📝 First 500 chars:\n{text[:500]}...")
        print(f"\n📝 Last 200 chars:\n{text[-200:]}")
        
    except FileNotFoundError:
        print(f"❌ File '{test_pdf}' not found!")
        print("Put a PDF in the same folder and try again")
        
    except Exception as e:
        print(f"❌ Error: {e}")