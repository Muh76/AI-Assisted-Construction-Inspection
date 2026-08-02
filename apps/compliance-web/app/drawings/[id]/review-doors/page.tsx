"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";

import { apiFetch } from "@/lib/api";

type Room = {
  id: number;
  project_id: number;
  name: string;
};

type Drawing = {
  id: number;
  project_id: number;
};

type DoorRow = {
  door_number: string;
  width: string;
  fire_rating: string;
  room_id: string;
};

type DoorSchedulePreviewResponse = {
  drawing_id: number;
  page_number: number;
  preview: boolean;
  rows: {
    door_number: string;
    width: number;
    fire_rating: string | null;
  }[];
};

type DoorScheduleConfirmResponse = {
  drawing_id: number;
  created: { id: number }[];
};

const inputClassName =
  "w-full rounded border border-zinc-300 bg-white px-2 py-1 text-sm text-zinc-900";

export default function ReviewDoorsPage() {
  const params = useParams<{ id: string }>();
  const drawingId = params.id;
  const [rooms, setRooms] = useState<Room[]>([]);
  const [pageNumber, setPageNumber] = useState("1");
  const [rows, setRows] = useState<DoorRow[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [isLoadingRooms, setIsLoadingRooms] = useState(true);
  const [isScanning, setIsScanning] = useState(false);
  const [isConfirming, setIsConfirming] = useState(false);
  const [hasScanned, setHasScanned] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function loadRooms() {
      setIsLoadingRooms(true);
      setError(null);

      try {
        const drawingResponse = await apiFetch(`/api/v1/drawings/${drawingId}`);

        if (!drawingResponse.ok) {
          throw new Error(await readErrorMessage(drawingResponse));
        }

        const drawing = (await drawingResponse.json()) as Drawing;

        const roomsResponse = await apiFetch("/api/v1/rooms");

        if (!roomsResponse.ok) {
          throw new Error(await readErrorMessage(roomsResponse));
        }

        const allRooms = (await roomsResponse.json()) as Room[];
        const projectRooms = allRooms.filter(
          (room) => room.project_id === drawing.project_id,
        );

        if (!cancelled) {
          setRooms(projectRooms);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load rooms");
        }
      } finally {
        if (!cancelled) {
          setIsLoadingRooms(false);
        }
      }
    }

    loadRooms();

    return () => {
      cancelled = true;
    };
  }, [drawingId]);

  async function handleScan(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSuccessMessage(null);
    setIsScanning(true);

    try {
      const response = await apiFetch(
        `/api/v1/drawings/${drawingId}/parse-doors?page_number=${pageNumber}`,
        { method: "POST" },
      );

      if (!response.ok) {
        throw new Error(await readErrorMessage(response));
      }

      const data = (await response.json()) as DoorSchedulePreviewResponse;
      const defaultRoomId = rooms.length > 0 ? String(rooms[0].id) : "";

      setRows(
        data.rows.map((row) => ({
          door_number: row.door_number,
          width: String(row.width),
          fire_rating: row.fire_rating ?? "",
          room_id: defaultRoomId,
        })),
      );
      setHasScanned(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to scan doors");
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
        `/api/v1/drawings/${drawingId}/parse-doors/confirm`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            rows: rows.map((row) => ({
              door_number: row.door_number,
              width: Number(row.width),
              fire_rating:
                row.fire_rating.trim() === "" ? null : row.fire_rating.trim(),
              room_id: Number(row.room_id),
            })),
          }),
        },
      );

      if (!response.ok) {
        throw new Error(await readErrorMessage(response));
      }

      const data = (await response.json()) as DoorScheduleConfirmResponse;
      setSuccessMessage(
        `Successfully created ${data.created.length} door${data.created.length === 1 ? "" : "s"}.`,
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to confirm doors");
    } finally {
      setIsConfirming(false);
    }
  }

  function updateRow(
    index: number,
    field: keyof DoorRow,
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

      <h1 className="mb-6 text-2xl font-semibold">Review extracted doors</h1>
      <p className="mb-8 text-sm text-zinc-600">Drawing #{drawingId}</p>

      {isLoadingRooms ? (
        <p className="mb-8 text-sm text-zinc-600">Loading rooms…</p>
      ) : rooms.length === 0 ? (
        <p className="mb-8 text-sm text-zinc-600">
          Add rooms to this project before reviewing extracted doors.
        </p>
      ) : (
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
      )}

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
          <p className="text-sm text-zinc-600">No door rows found on this page.</p>
        ) : (
          <>
            <table className="mb-6 w-full border-collapse text-left text-sm">
              <thead>
                <tr className="border-b border-zinc-300">
                  <th className="py-2 pr-2 font-medium">Door number</th>
                  <th className="py-2 pr-2 font-medium">Width</th>
                  <th className="py-2 pr-2 font-medium">Fire rating</th>
                  <th className="py-2 pr-2 font-medium">Room</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row, index) => (
                  <tr key={index} className="border-b border-zinc-200">
                    <td className="py-2 pr-2">
                      <input
                        type="text"
                        value={row.door_number}
                        onChange={(event) =>
                          updateRow(index, "door_number", event.target.value)
                        }
                        className={inputClassName}
                      />
                    </td>
                    <td className="py-2 pr-2">
                      <input
                        type="number"
                        value={row.width}
                        onChange={(event) =>
                          updateRow(index, "width", event.target.value)
                        }
                        min="0"
                        step="any"
                        className={inputClassName}
                      />
                    </td>
                    <td className="py-2 pr-2">
                      <input
                        type="text"
                        value={row.fire_rating}
                        onChange={(event) =>
                          updateRow(index, "fire_rating", event.target.value)
                        }
                        className={inputClassName}
                      />
                    </td>
                    <td className="py-2 pr-2">
                      <select
                        value={row.room_id}
                        onChange={(event) =>
                          updateRow(index, "room_id", event.target.value)
                        }
                        required
                        className={inputClassName}
                      >
                        {rooms.map((room) => (
                          <option key={room.id} value={room.id}>
                            {room.name}
                          </option>
                        ))}
                      </select>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            <button
              type="button"
              onClick={handleConfirm}
              disabled={isConfirming || rooms.length === 0}
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
