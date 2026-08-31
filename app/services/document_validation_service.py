

import hashlib
from typing import Optional


TRUSTED_SOURCES = [
    "world health organization",
    "who",
    "who model formulary",
    "who essential medicines",
    "ministry of health",
    "centers for disease control",
    "cdc",
    "national institutes of health",
    "nih",
    "indian council of medical research",
    "icmr",
    "lancet",
    "new england journal of medicine",
    "nejm",
    "british medical journal",
    "bmj",
]


class DocumentValidationService:
    

    def validate_file_type(self, filename: str, content_type: str) -> dict:
        
        if not filename.lower().endswith(".pdf") and content_type != "application/pdf":
            return {"valid": False, "error": "Only PDF files are accepted"}
        return {"valid": True}

    def generate_hash(self, file_content: bytes) -> str:
        
        return hashlib.sha256(file_content).hexdigest()

    def extract_metadata(self, file_content: bytes) -> dict:
        
        metadata = {"publisher": None, "isbn": None}

        try:
            import pdfplumber
            import tempfile
            import os

            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(file_content)
                tmp_path = tmp.name

            try:
                with pdfplumber.open(tmp_path) as pdf:
                    info = pdf.metadata or {}
                    metadata["publisher"] = info.get("Author") or info.get("Creator") or None

                    for page in pdf.pages[:3]:
                        text = page.extract_text() or ""
                        text_lower = text.lower()

                        import re
                        isbn_match = re.search(r"isbn[:\s]*([\d\-]+)", text_lower)
                        if isbn_match:
                            metadata["isbn"] = isbn_match.group(1)
                            break

                        who_ref = re.search(r"who/[a-z]+/[a-z]+/[\d.]+", text_lower)
                        if who_ref:
                            metadata["isbn"] = who_ref.group(0).upper()
                            break
            finally:
                os.unlink(tmp_path)

        except Exception:
            pass

        return metadata

    def check_source_whitelist(self, publisher: Optional[str], text_sample: str = "") -> bool:
        
        check_text = (publisher or "").lower() + " " + text_sample[:2000].lower()

        for source in TRUSTED_SOURCES:
            if source in check_text:
                return True
        return False

    def validate_document(self, filename: str, content_type: str, file_content: bytes) -> dict:
        

        type_check = self.validate_file_type(filename, content_type)
        if not type_check["valid"]:
            return {
                "valid": False,
                "status": "rejected",
                "error": type_check["error"],
            }

        file_hash = self.generate_hash(file_content)

        metadata = self.extract_metadata(file_content)

        text_sample = ""
        try:
            import pdfplumber
            import tempfile
            import os
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(file_content)
                tmp_path = tmp.name
            try:
                with pdfplumber.open(tmp_path) as pdf:
                    if pdf.pages:
                        text_sample = pdf.pages[0].extract_text() or ""
            finally:
                os.unlink(tmp_path)
        except Exception:
            pass

        source_trusted = self.check_source_whitelist(metadata.get("publisher"), text_sample)

        return {
            "valid": True,
            "status": "pending_approval",
            "file_hash": file_hash,
            "publisher": metadata.get("publisher"),
            "isbn_reference": metadata.get("isbn"),
            "source_trusted": source_trusted,
            "validation_notes": (
                "Source matches trusted whitelist" if source_trusted
                else "Source not in whitelist — requires manual verification"
            ),
        }
