import axios from "axios";

// Backend base URL can be overridden via VITE_API_BASE_URL.
const apiBase = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/$/, "");
const api = axios.create({
  baseURL: apiBase ? `${apiBase}/api/ocr` : "/api/ocr",
  timeout: 30000,
});

export async function uploadDocument(file, options = {}) {
  const formData = new FormData();
  formData.append("file", file);
  const forcedDocType = (options.forcedDocType || "").trim();
  if (forcedDocType) {
    formData.append("forced_doc_type", forcedDocType);
  }

  const response = await api.post("/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
    timeout: 120000,
  });
  return response.data;
}

export async function uploadBatch(files, options = {}) {
  const formData = new FormData();
  files.forEach((file) => {
    formData.append("files", file);
  });
  const forcedDocType = (options.forcedDocType || "").trim();
  if (forcedDocType) {
    formData.append("forced_doc_type", forcedDocType);
  }

  const response = await api.post("/batch/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
    timeout: 300000,
  });
  return response.data;
}

export async function fetchBatchHistory(limit = 10) {
  const response = await api.get("/batch", { params: { limit } });
  return response.data;
}

export async function fetchBatchDetail(batchId) {
  const response = await api.get(`/batch/${batchId}`);
  return response.data;
}

export async function fetchDocuments() {
  const response = await api.get("/documents");
  return response.data;
}

export async function processWithLlama({
  text,
  instruction,
  documentId,
  syncData = false,
}) {
  const response = await api.post(
    "/process_with_llama",
    {
      text,
      instruction,
      document_id: documentId ?? null,
      sync_data: Boolean(syncData),
    },
    {
      timeout: 300000,
    }
  );
  return response.data;
}

export async function saveDocumentData({ documentId, data, merge = true }) {
  const response = await api.put(
    `/documents/${documentId}/data`,
    {
      data,
      merge: Boolean(merge),
    },
    {
      timeout: 120000,
    }
  );
  return response.data;
}

export async function askDocumentQuestion({ documentId, question }) {
  const response = await api.post(
    `/documents/${documentId}/ask`,
    { question },
    { timeout: 180000 }
  );
  return response.data;
}
