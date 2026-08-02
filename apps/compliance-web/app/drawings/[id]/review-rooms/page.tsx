"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { FormEvent, useState } from "react";

import { apiFetch } from "@/lib/api";

type RoomRow = {
  name: string;
  occupancy_category: string;
  floor_area: string;
  occupant_load: string;
};

type RoomSchedulePreviewResponse = {
  drawing_id: number;
  page_number: number;
  preview: boolean;
  rows: {
    name: string;
    occupancy_category: string;
    floor_area: number;
    occupant_load: number;
  }[];
};

type RoomScheduleConfirmResponse = {
  drawing_id: number;
  created: { id: number }[];
};

const inputClassName =
  "w-full rounded border border-zinc-300 bg-white px-2 py-1 text-sm text-zinc-900";

export default function ReviewRoomsPage() {
  const params = useParams<{ id: string }>();
  const drawingId = params.id;
  const [pageNumber, setPageNumber] = useState("1");
  const [rows, setRows] = useState<RoomRow[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [isScanning, setIsScanning] = useState(false);
  const [isConfirming, setIsConfirming] = useState(false);
  const [hasScanned, setHasScanned] = useState(false);

  async function handleScan(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSuccessMessage(null);
    setIsScanning(true);

    try {
      const response = await apiFetch(
        `/api/v1/drawings/${drawingId}/parse-rooms?page_number=${pageNumber}`,
        { method: "POST" },
      );

      if (!response.ok) {
        throw new Error(await readErrorMessage(response));
      }

      const data = (await response.json()) as RoomSchedulePreviewResponse;
      setRows(
        data.rows.map((row) => ({
          name: row.name,
          occupancy_category: row.occupancy_category,
          floor_area: String(row.floor_area),
          occupant_load: String(row.occupant_load),
        })),
      );
      setHasScanned(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to scan rooms");
    } finally {
      setIsScanning(false);
    }
  }

  async function handleConfirm() {
    setError(null);
    setSuccessMessage(null);
    setIsConfirming(true);

    try {
      const response = await apiFetch(
        `/api/v1/drawings/${drawingId}/parse-rooms/confirm`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            rows: rows.map((row) => ({
              name: row.name,
              occupancy_category: row.occupancy_category,
              floor_area: Number(row.floor_area),
              occupant_load: Number(row.occupant_load),
            })),
          }),
        },
      );

      if (!response.ok) {
        throw new Error(await readErrorMessage(response));
      }

      const data = (await response.json()) as RoomScheduleConfirmResponse;
      setSuccessMessage(
        `Successfully created ${data.created.length} room${data.created.length === 1 ? "" : "s"}.`,
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to confirm rooms");
    } finally {
      setIsConfirming(false);
    }
  }

  function updateRow(
    index: number,
    field: keyof RoomRow,
    value: string,
  ): void {
    setRows((current) =>
      current.map((row, rowIndex) =>
        rowIndex === index ? { ...row, [field]: value } : row,
      ),
    );
  }

  return (
    <main className="mx-auto w-full max-w-4xl flex-1 px-4 py-16">
      <p className="mb-4 text-sm">
        <Link href="/projects" className="text-zinc-600 underline">
          ← Back to projects
        </Link>
      </p>

      <h1 className="mb-6 text-2xl font-semibold">Review extracted rooms</h1>
      <p className="mb-8 text-sm text-zinc-600">Drawing #{drawingId}</p>

      <form onSubmit={handleScan} className="mb-8 flex flex-wrap items-end gap-4">
        <label className="flex flex-col gap-1 text-sm">
          <span>Page number</span>
          <input
            type="number"
            name="page_number"
            value={pageNumber}
            onChange={(event) => setPageNumber(event.target.value)}
            required
            min="1"
            step="1"
            className="w-24 rounded border border-zinc-300 bg-white px-3 py-2 text-base text-zinc-900"
          />
        </label>

        <button
          type="submit"
          disabled={isScanning}
          className="rounded bg-zinc-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
        >
          {isScanning ? "Scanning…" : "Scan"}
        </button>
      </form>

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

      {hasScanned ? (
        rows.length === 0 ? (
          <p className="text-sm text-zinc-600">No room rows found on this page.</p>
        ) : (
          <>
            <table className="mb-6 w-full border-collapse text-left text-sm">
              <thead>
                <tr className="border-b border-zinc-300">
                  <th className="py-2 pr-2 font-medium">Name</th>
                  <th className="py-2 pr-2 font-medium">Occupancy</th>
                  <th className="py-2 pr-2 font-medium">Floor area</th>
                  <th className="py-2 pr-2 font-medium">Occupant load</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row, index) => (
                  <tr key={index} className="border-b border-zinc-200">
                    <td className="py-2 pr-2">
                      <input
                        type="text"
                        value={row.name}
                        onChange={(event) =>
                          updateRow(index, "name", event.target.value)
                        }
                        className={inputClassName}
                      />
                    </td>
                    <td className="py-2 pr-2">
                      <input
                        type="text"
                        value={row.occupancy_category}
                        onChange={(event) =>
                          updateRow(index, "occupancy_category", event.target.value)
                        }
                        className={inputClassName}
                      />
                    </td>
                    <td className="py-2 pr-2">
                      <input
                        type="number"
                        value={row.floor_area}
                        onChange={(event) =>
                          updateRow(index, "floor_area", event.target.value)
                        }
                        min="0"
                        step="any"
                        className={inputClassName}
                      />
                    </td>
                    <td className="py-2 pr-2">
                      <input
                        type="number"
                        value={row.occupant_load}
                        onChange={(event) =>
                          updateRow(index, "occupant_load", event.target.value)
                        }
                        min="0"
                        step="1"
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
