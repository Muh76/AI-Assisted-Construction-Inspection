"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { apiFetch } from "@/lib/api";

type CorridorCalloutRow = {
  label: string;
  width_mm: string;
  approximate_location: string;
  length: string;
};

type CorridorVisionPreviewResponse = {
  drawing_id: number;
  page_number: number;
  preview: boolean;
  image_path: string;
  callouts: {
    label: string;
    width_mm: number;
    approximate_location: string;
  }[];
};

type CorridorVisionConfirmResponse = {
  drawing_id: number;
  page_number: number;
  created: { id: number }[];
};

const inputClassName =
  "w-full rounded border border-zinc-300 bg-white px-2 py-1 text-sm text-zinc-900";

export default function ReviewCorridorsPage() {
  const params = useParams<{ id: string; page: string }>();
  const drawingId = params.id;
  const pageNumber = params.page;
  const [callouts, setCallouts] = useState<CorridorCalloutRow[]>([]);
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isConfirming, setIsConfirming] = useState(false);
  const [hasLoaded, setHasLoaded] = useState(false);

  useEffect(() => {
    let cancelled = false;
    let objectUrl: string | null = null;

    async function loadPage() {
      setIsLoading(true);
      setError(null);
      setSuccessMessage(null);

      try {
        const renderResponse = await apiFetch(
          `/api/v1/drawings/${drawingId}/pages/${pageNumber}/render`,
          { method: "POST" },
        );

        if (!renderResponse.ok) {
          throw new Error(await readErrorMessage(renderResponse));
        }

        const imageResponse = await apiFetch(
          `/api/v1/drawings/${drawingId}/pages/${pageNumber}/image`,
        );

        if (!imageResponse.ok) {
          throw new Error(await readErrorMessage(imageResponse));
        }

        const blob = await imageResponse.blob();
        objectUrl = URL.createObjectURL(blob);

        const parseResponse = await apiFetch(
          `/api/v1/drawings/${drawingId}/pages/${pageNumber}/parse-corridors`,
          { method: "POST" },
        );

        if (!parseResponse.ok) {
          throw new Error(await readErrorMessage(parseResponse));
        }

        const data = (await parseResponse.json()) as CorridorVisionPreviewResponse;

        if (!cancelled) {
          setImageUrl(objectUrl);
          setCallouts(
            data.callouts.map((callout) => ({
              label: callout.label,
              width_mm: String(callout.width_mm),
              approximate_location: callout.approximate_location,
              length: "",
            })),
          );
          setHasLoaded(true);
        }
      } catch (err) {
        if (objectUrl) {
          URL.revokeObjectURL(objectUrl);
        }
        if (!cancelled) {
          setError(
            err instanceof Error ? err.message : "Failed to load corridor review",
          );
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    loadPage();

    return () => {
      cancelled = true;
    };
  }, [drawingId, pageNumber]);

  useEffect(() => {
    return () => {
      if (imageUrl) {
        URL.revokeObjectURL(imageUrl);
      }
    };
  }, [imageUrl]);

  async function handleConfirm() {
    setError(null);
    setSuccessMessage(null);
    setIsConfirming(true);

    try {
      const response = await apiFetch(
        `/api/v1/drawings/${drawingId}/pages/${pageNumber}/parse-corridors/confirm`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            callouts: callouts.map((callout) => ({
              label: callout.label,
              width_mm: Number(callout.width_mm),
              approximate_location: callout.approximate_location,
              length: Number(callout.length),
            })),
          }),
        },
      );

      if (!response.ok) {
        throw new Error(await readErrorMessage(response));
      }

      const data = (await response.json()) as CorridorVisionConfirmResponse;
      setSuccessMessage(
        `Successfully created ${data.created.length} corridor${data.created.length === 1 ? "" : "s"}.`,
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to confirm corridors");
    } finally {
      setIsConfirming(false);
    }
  }

  function updateCallout(
    index: number,
    field: keyof CorridorCalloutRow,
    value: string,
  ): void {
    setCallouts((current) =>
      current.map((callout, calloutIndex) =>
        calloutIndex === index ? { ...callout, [field]: value } : callout,
      ),
    );
  }

  return (
    <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-16">
      <p className="mb-4 text-sm">
        <Link href="/projects" className="text-zinc-600 underline">
          ← Back to projects
        </Link>
      </p>

      <h1 className="mb-2 text-2xl font-semibold">Review corridor widths</h1>
      <p className="mb-8 text-sm text-zinc-600">
        Drawing #{drawingId} · Page {pageNumber}
      </p>

      {isLoading ? (
        <p className="text-sm text-zinc-600">Rendering page and scanning corridors…</p>
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
        <div className="flex flex-col gap-8 lg:flex-row lg:items-start">
          <div className="lg:w-1/2">
            {imageUrl ? (
              <img
                src={imageUrl}
                alt={`Drawing ${drawingId} page ${pageNumber}`}
                className="w-full rounded border border-zinc-200"
              />
            ) : (
              <p className="text-sm text-zinc-600">Image unavailable.</p>
            )}
          </div>

          <div className="lg:w-1/2">
            {callouts.length === 0 ? (
              <p className="text-sm text-zinc-600">No corridor callouts found.</p>
            ) : (
              <>
                <table className="mb-6 w-full border-collapse text-left text-sm">
                  <thead>
                    <tr className="border-b border-zinc-300">
                      <th className="py-2 pr-2 font-medium">Label</th>
                      <th className="py-2 pr-2 font-medium">Width (mm)</th>
                      <th className="py-2 pr-2 font-medium">Location</th>
                      <th className="py-2 pr-2 font-medium">Length</th>
                    </tr>
                  </thead>
                  <tbody>
                    {callouts.map((callout, index) => (
                      <tr key={index} className="border-b border-zinc-200">
                        <td className="py-2 pr-2">
                          <input
                            type="text"
                            value={callout.label}
                            onChange={(event) =>
                              updateCallout(index, "label", event.target.value)
                            }
                            className={inputClassName}
                          />
                        </td>
                        <td className="py-2 pr-2">
                          <input
                            type="number"
                            value={callout.width_mm}
                            onChange={(event) =>
                              updateCallout(index, "width_mm", event.target.value)
                            }
                            min="0"
                            step="any"
                            className={inputClassName}
                          />
                        </td>
                        <td className="py-2 pr-2">
                          <input
                            type="text"
                            value={callout.approximate_location}
                            onChange={(event) =>
                              updateCallout(
                                index,
                                "approximate_location",
                                event.target.value,
                              )
                            }
                            className={inputClassName}
                          />
                        </td>
                        <td className="py-2 pr-2">
                          <input
                            type="number"
                            value={callout.length}
                            onChange={(event) =>
                              updateCallout(index, "length", event.target.value)
                            }
                            required
                            min="0"
                            step="any"
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
                  {isConfirming ? "Confirming…" : "Confirm"}
                </button>
              </>
            )}
          </div>
        </div>
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
