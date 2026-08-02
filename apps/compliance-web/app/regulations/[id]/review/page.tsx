"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { apiFetch } from "@/lib/api";

type ClauseRow = {
  section: string;
  text: string;
  threshold_value: string;
  threshold_unit: string;
};

type RegulationClausePreviewResponse = {
  document_id: number;
  preview: boolean;
  clauses: {
    section: string;
    text: string;
    page_number: number;
  }[];
};

type RegulationClauseConfirmResponse = {
  document_id: number;
  created: { id: number }[];
  updated: { id: number }[];
};

const inputClassName =
  "w-full rounded border border-zinc-300 bg-white px-2 py-1 text-sm text-zinc-900";

export default function RegulationReviewPage() {
  const params = useParams<{ id: string }>();
  const documentId = params.id;
  const [clauses, setClauses] = useState<ClauseRow[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isConfirming, setIsConfirming] = useState(false);
  const [hasLoaded, setHasLoaded] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function loadClauses() {
      setIsLoading(true);
      setError(null);
      setSuccessMessage(null);

      try {
        const response = await apiFetch(
          `/api/v1/regulations/documents/${documentId}/parse-clauses`,
          { method: "POST" },
        );

        if (!response.ok) {
          throw new Error(await readErrorMessage(response));
        }

        const data = (await response.json()) as RegulationClausePreviewResponse;

        if (!cancelled) {
          setClauses(
            data.clauses.map((clause) => ({
              section: clause.section,
              text: clause.text,
              threshold_value: "",
              threshold_unit: "",
            })),
          );
          setHasLoaded(true);
        }
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof Error ? err.message : "Failed to parse clauses",
          );
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    loadClauses();

    return () => {
      cancelled = true;
    };
  }, [documentId]);

  async function handleConfirm() {
    setError(null);
    setSuccessMessage(null);
    setIsConfirming(true);

    try {
      const response = await apiFetch(
        `/api/v1/regulations/documents/${documentId}/parse-clauses/confirm`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            clauses: clauses.map((clause) => ({
              section: clause.section,
              text: clause.text,
              threshold_value:
                clause.threshold_value.trim() === ""
                  ? null
                  : Number(clause.threshold_value),
              threshold_unit:
                clause.threshold_unit.trim() === ""
                  ? null
                  : clause.threshold_unit.trim(),
            })),
          }),
        },
      );

      if (!response.ok) {
        throw new Error(await readErrorMessage(response));
      }

      const data = (await response.json()) as RegulationClauseConfirmResponse;
      const createdCount = data.created.length;
      const updatedCount = data.updated.length;
      setSuccessMessage(
        `Saved ${createdCount} new clause${createdCount === 1 ? "" : "s"} and updated ${updatedCount} existing clause${updatedCount === 1 ? "" : "s"}.`,
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to confirm clauses");
    } finally {
      setIsConfirming(false);
    }
  }

  function updateClause(
    index: number,
    field: keyof ClauseRow,
    value: string,
  ): void {
    setClauses((current) =>
      current.map((clause, clauseIndex) =>
        clauseIndex === index ? { ...clause, [field]: value } : clause,
      ),
    );
  }

  return (
    <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-16">
      <p className="mb-4 text-sm">
        <Link href="/regulations" className="text-zinc-600 underline">
          ← Back to regulations
        </Link>
      </p>

      <h1 className="mb-2 text-2xl font-semibold">Review regulation clauses</h1>
      <p className="mb-8 text-sm text-zinc-600">Document #{documentId}</p>

      {isLoading ? (
        <p className="text-sm text-zinc-600">Parsing candidate clauses…</p>
      ) : null}

      {error ? (
        <p className="mb-4 text-sm text-red-600" role="alert">
          {error}
        </p>
      ) : null}

      {successMessage ? (
        <p className="mb-4 text-sm text-green-700" role="status">
          {successMessage}
        </p>
      ) : null}

      {hasLoaded ? (
        clauses.length === 0 ? (
          <p className="text-sm text-zinc-600">No candidate clauses found.</p>
        ) : (
          <>
            <table className="mb-6 w-full border-collapse text-left text-sm">
              <thead>
                <tr className="border-b border-zinc-300">
                  <th className="py-2 pr-2 font-medium">Section</th>
                  <th className="py-2 pr-2 font-medium">Text</th>
                  <th className="py-2 pr-2 font-medium">Threshold value</th>
                  <th className="py-2 pr-2 font-medium">Threshold unit</th>
                </tr>
              </thead>
              <tbody>
                {clauses.map((clause, index) => (
                  <tr key={index} className="border-b border-zinc-200 align-top">
                    <td className="py-2 pr-2">
                      <input
                        type="text"
                        value={clause.section}
                        onChange={(event) =>
                          updateClause(index, "section", event.target.value)
                        }
                        className={inputClassName}
                      />
                    </td>
                    <td className="py-2 pr-2">
                      <textarea
                        value={clause.text}
                        onChange={(event) =>
                          updateClause(index, "text", event.target.value)
                        }
                        rows={3}
                        className={inputClassName}
                      />
                    </td>
                    <td className="py-2 pr-2">
                      <input
                        type="number"
                        value={clause.threshold_value}
                        onChange={(event) =>
                          updateClause(index, "threshold_value", event.target.value)
                        }
                        min="0"
                        step="any"
                        className={inputClassName}
                      />
                    </td>
                    <td className="py-2 pr-2">
                      <input
                        type="text"
                        value={clause.threshold_unit}
                        onChange={(event) =>
                          updateClause(index, "threshold_unit", event.target.value)
                        }
                        className={inputClassName}
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            <button
              type="button"
              onClick={handleConfirm}
              disabled={isConfirming}
              className="rounded bg-zinc-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
            >
              {isConfirming ? "Saving…" : "Confirm"}
            </button>
          </>
        )
      ) : null}
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
