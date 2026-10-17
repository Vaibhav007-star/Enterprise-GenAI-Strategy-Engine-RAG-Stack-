import streamlit as st
import sys
import tempfile
from pathlib import Path

root_path = Path(__file__).resolve().parent.parent
if str(root_path) not in sys.path:
    sys.path.insert(0, str(root_path))

from src.engine import get_engine
from src.security.sanitizer import SecuritySanitizer
from src.utils.ui_helpers import render_header, render_metric_card, load_custom_css

st.set_page_config(page_title="Document Library | Strategy Engine", page_icon="📑", layout="wide")
load_custom_css()

render_header(
    title="Enterprise Document Library",
    subtitle="Ingest, validate, chunk, and index corporate documents with content hash deduplication",
    badge_text="Document Vault",
    badge_type="online"
)

engine = get_engine()

# Layout: Ingestion Controls & Upload Area
col_upload, col_settings = st.columns([7, 5])

with col_upload:
    st.markdown("#### 📤 Upload Documents")
    uploaded_files = st.file_uploader(
        "Select enterprise files (PDF, DOCX, CSV, XLSX, MD, TXT):",
        accept_multiple_files=True,
        type=["pdf", "docx", "csv", "xlsx", "xls", "md", "txt"]
    )

with col_settings:
    st.markdown("#### ⚙️ Chunking Strategy")
    chunk_strategy = st.selectbox(
        "Ingestion Chunking Strategy:",
        options=["parent_child", "structure_aware", "recursive"],
        format_func=lambda x: {
            "parent_child": "Parent-Child (Broad context + precise child matches)",
            "structure_aware": "Structure-Aware (Respects headings and sections)",
            "recursive": "Recursive Character (Sliding window)"
        }.get(x, x),
        help="Parent-Child is recommended for complex enterprise policies and contracts."
    )
    force_reindex = st.checkbox("Force Re-indexing (ignore duplicate content hash)", value=False)

if uploaded_files:
    if st.button("🚀 Process and Index Uploaded Documents", type="primary", use_container_width=True):
        progress_bar = st.progress(0)
        status_box = st.empty()

        for idx, file in enumerate(uploaded_files):
            status_box.info(f"Processing `{file.name}`...")
            
            # Security validation
            valid, err = SecuritySanitizer.validate_file_upload(file.name, file.size)
            if not valid:
                st.error(f"❌ Security rejection for '{file.name}': {err}")
                continue

            # Save to temporary buffer
            with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.name).suffix) as tmp:
                tmp.write(file.getvalue())
                tmp_path = Path(tmp.name)

            # Target upload path
            dest_path = engine.settings.upload_dir / file.name
            dest_path.write_bytes(file.getvalue())

            # Ingest through unified pipeline
            result = engine.ingestion_pipeline.ingest_file(
                source_path=dest_path,
                chunking_strategy=chunk_strategy,
                force_reindex=force_reindex
            )

            progress_bar.progress((idx + 1) / len(uploaded_files))

            if result.success:
                if result.is_duplicate:
                    st.warning(f"⚠️ `{file.name}`: {result.warning}")
                else:
                    st.success(f"✅ Ingested `{file.name}` — Indexed {result.chunks_indexed} chunks & {result.tables_indexed} tables.")
            else:
                st.error(f"❌ Failed to ingest `{file.name}`: {result.error}")

        # Refresh BM25 index with new chunks
        engine.retriever.refresh_bm25_index()
        status_box.success("All uploads processed successfully!")
        st.rerun()

st.markdown("---")

# Active Indexed Documents Table
st.markdown("### 🗃️ Active Document Registry")
docs = engine.document_store.get_all_documents()

if docs:
    for doc in docs:
        with st.expander(f"📄 {doc['file_name']} — {doc['file_type'].upper()} ({doc['file_size_bytes']/1024:.1f} KB)"):
            c1, c2, c3 = st.columns([3, 3, 2])
            with c1:
                st.markdown(f"**Document ID:** `{doc['document_id']}`")
                st.markdown(f"**Content Hash:** `{doc['content_hash'][:16]}...`")
                st.markdown(f"**Pages / Sheets:** `{doc['total_pages_or_sheets']}`")
            with c2:
                st.markdown(f"**Extracted Sections:** `{doc['sections_count']}`")
                st.markdown(f"**Extracted Tables:** `{doc['tables_count']}`")
                st.markdown(f"**Ingested At:** `{doc['ingested_at'][:19]}`")
            with c3:
                st.markdown("**Actions:**")
                if st.button("🗑️ Delete Document", key=f"del_{doc['document_id']}", use_container_width=True):
                    deleted = engine.ingestion_pipeline.delete_document(doc["document_id"])
                    if deleted:
                        engine.retriever.refresh_bm25_index()
                        st.success(f"Purged `{doc['file_name']}` from vector index and registry.")
                        st.rerun()
else:
    st.info("No documents are currently stored in the library. Upload documents above to begin.")
