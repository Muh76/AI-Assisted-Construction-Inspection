"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useState } from "react";

import { apiFetch } from "@/lib/api";

type RegulationDocument = {
  id: number;
  code: string;
  edition: string;
  file_path: string;
  uploaded_at: string;
};

const inputClassName =
  "rounded border border-zinc-300 bg-white px-3 py-2 text-base text-zinc-900";

export default function RegulationsPage() {
  const [documents, setDocuments] = useState<RegulationDocument[]>([]);
  const [code, setCode] = useState("");
  const [edition, setEdition] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [selectedDocumentId, setSelectedDocumentId] = useState("");
  const [startPage, setStartPage] = useState("1");
  const [endPage, setEndPage] = useState("1");
  const [error, setError] = useState<string | null>(null);
  const [extractMessage, setExtractMessage] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isUploading, setIsUploading] = useState(false);
  const [isExtracting, setIsExtracting] = useState(false);

  const loadDocuments = useCallback(async () => {
    setError(null);

    const response = await apiFetch("/api/v1/regulations/documents");

    if (!response.ok) {
      throw new Error(await readErrorMessage(response));
    }

    const data = (await response.json()) as RegulationDocument[];
    setDocuments(data);

    setSelectedDocumentId((current) => {
      if (current && data.some((document) => String(document.id) === current)) {
        return current;
      }
      return data.length > 0 ? String(data[0].id) : "";
    });
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function fetchDocuments() {
      setIsLoading(true);
      try {
        await loadDocuments();
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof Error ? err.message : "Failed to load documents",
          );
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    fetchDocuments();

    return () => {
      cancelled = true;
    };
  }, [loadDocuments]);

  async function handleUpload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file) {
      setError("Select a PDF file to upload.");
      return;
    }

    setError(null);
    setExtractMessage(null);
    setIsUploading(true);

    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("code", code);
      formData.append("edition", edition);

      const response = await apiFetch("/api/v1/regulations/documents", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        throw new Error(await readErrorMessage(response));
      }

      const document = (await response.json()) as RegulationDocument;

      setCode("");
      setEdition("");
      setFile(null);
      event.currentTarget.reset();
      setSelectedDocumentId(String(document.id));
      await loadDocuments();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to upload document");
    } finally {
      setIsUploading(false);
    }
  }

  async function handleExtract(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!selectedDocumentId) {
      setError("Upload a document before extracting pages.");
      return;
    }

    setError(null);
    setExtractMessage(null);
    setIsExtracting(true);

    try {
      const response = await apiFetch(
        `/api/v1/regulations/documents/${selectedDocumentId}/extract?start=${startPage}&end=${endPage}`,
        { method: "POST" },
      );

      if (!response.ok) {
        throw new Error(await readErrorMessage(response));
      }

      const data = (await response.json()) as {
        pages_processed: number;
        start_page: number;
        end_page: number;
      };

      setExtractMessage(
        `Extracted ${data.pages_processed} page${data.pages_processed === 1 ? "" : "s"} (pages ${data.start_page}–${data.end_page}).`,
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to extract pages");
    } finally {
      setIsExtracting(false);
    }
  }

  function documentFileName(filePath: string): string {
    return filePath.split("/").pop() ?? filePath;
  }

  return (
    <main className="mx-auto w-full max-w-3xl flex-1 px-4 py-16">
      <p className="mb-4 text-sm">
        <Link href="/projects" className="text-zinc-600 underline">
          ← Back to projects
        </Link>
      </p>

      <h1 className="mb-8 text-2xl font-semibold">Regulations</h1>

      <section className="mb-10">
        <h2 className="mb-4 text-lg font-medium">Upload document</h2>
        <form onSubmit={handleUpload} className="grid gap-4 sm:grid-cols-2">
          <label className="flex flex-col gap-1 text-sm">
            <span>Code</span>
            <input
              type="text"
              name="code"
              value={code}
              onChange={(event) => setCode(event.target.value)}
              required
              placeholder="OBC"
              className={inputClassName}
            />
          </label>

          <label className="flex flex-col gap-1 text-sm">
            <span>Edition</span>
            <input
              type="text"
              name="edition"
              value={edition}
              onChange={(event) => setEdition(event.target.value)}
              required
              placeholder="2020"
              className={inputClassName}
            />
          </label>

          <label className="flex flex-col gap-1 text-sm sm:col-span-2">
            <span>PDF file</span>
            <input
              type="file"
              name="file"
              accept=".pdf,application/pdf"
              onChange={(event) => setFile(event.target.files?.[0] ?? null)}
              required
              className="text-sm text-zinc-900"
            />
          </label>

          <div className="sm:col-span-2">
            <button
              type="submit"
              disabled={isUploading}
              className="rounded bg-zinc-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
            >
              {isUploading ? "Uploading…" : "Upload"}
            </button>
          </div>
        </form>
      </section>

      <section className="mb-10">
        <h2 className="mb-4 text-lg font-medium">Extract pages</h2>
        {documents.length === 0 ? (
          <p className="text-sm text-zinc-600">
            Upload a regulation document to extract page text.
          </p>
        ) : (
          <form onSubmit={handleExtract} className="grid gap-4 sm:grid-cols-2">
            <label className="flex flex-col gap-1 text-sm sm:col-span-2">
              <span>Document</span>
              <select
                name="document_id"
                value={selectedDocumentId}
                onChange={(event) => setSelectedDocumentId(event.target.value)}
                required
                className={inputClassName}
              >
                {documents.map((document) => (
                  <option key={document.id} value={document.id}>
                    {document.code} {document.edition} —{" "}
                    {documentFileName(document.file_path)}
                  </option>
                ))}
              </select>
            </label>

            <label className="flex flex-col gap-1 text-sm">
              <span>Start page</span>
              <input
                type="number"
                name="start_page"
                value={startPage}
                onChange={(event) => setStartPage(event.target.value)}
                required
                min="1"
                step="1"
                className={inputClassName}
              />
            </label>

            <label className="flex flex-col gap-1 text-sm">
              <span>End page</span>
              <input
                type="number"
                name="end_page"
                value={endPage}
                onChange={(event) => setEndPage(event.target.value)}
                required
                min="1"
                step="1"
                className={inputClassName}
              />
            </label>

            <div className="sm:col-span-2">
              <button
                type="submit"
                disabled={isExtracting}
                className="rounded bg-zinc-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
              >
                {isExtracting ? "Extracting…" : "Extract"}
              </button>
            </div>
          </form>
        )}
      </section>

      {error ? (
        <p className="mb-4 text-sm text-red-600" role="alert">
          {error}
        </p>
      ) : null}

      {extractMessage ? (
        <p className="mb-4 text-sm text-green-700" role="status">
          {extractMessage}
        </p>
      ) : null}

      <section>
        <h2 className="mb-4 text-lg font-medium">Uploaded documents</h2>

        {isLoading ? (
          <p className="text-sm text-zinc-600">Loading documents…</p>
        ) : documents.length === 0 ? (
          <p className="text-sm text-zinc-600">No documents yet.</p>
        ) : (
          <table className="w-full border-collapse text-left text-sm">
            <thead>
              <tr className="border-b border-zinc-300">
                <th className="py-2 pr-4 font-medium">Code</th>
                <th className="py-2 pr-4 font-medium">Edition</th>
                <th className="py-2 pr-4 font-medium">File</th>
                <th className="py-2 pr-4 font-medium">Uploaded</th>
              </tr>
            </thead>
            <tbody>
              {documents.map((document) => (
                <tr key={document.id} className="border-b border-zinc-200">
                  <td className="py-2 pr-4">{document.code}</td>
                  <td className="py-2 pr-4">{document.edition}</td>
                  <td className="py-2 pr-4">
                    {documentFileName(document.file_path)}
                  </td>
                  <td className="py-2 pr-4">
                    {new Date(document.uploaded_at).toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </main>
  );
}

async function readErrorMessage(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: string | unknown };
    if (typeof body.detail === "string") {
      return body.detail;
    }
  } catch {
    // Fall through to status-based message.
  }

  return `Request failed with status ${response.status}`;
}
