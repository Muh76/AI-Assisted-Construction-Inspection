"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { FormEvent, useCallback, useEffect, useState } from "react";

import { apiFetch } from "@/lib/api";

type Project = {
  id: number;
  name: string;
  owner_id: number;
};

type Room = {
  id: number;
  project_id: number;
  name: string;
  occupancy_category: string;
  floor_area: number;
  occupant_load: number;
};

type Door = {
  id: number;
  room_id: number;
  clear_width: number;
  fire_rating: string | null;
};

type Corridor = {
  id: number;
  project_id: number;
  clear_width: number;
  length: number;
};

type Exit = {
  id: number;
  project_id: number;
  location: string;
  clear_width: number;
  is_required_exit: boolean;
};

type FireProtectionItemType =
  | "fire_extinguisher"
  | "penetration_seal"
  | "fire_separation";

type FireProtectionItem = {
  id: number;
  project_id: number;
  item_type: FireProtectionItemType;
  location: string;
  rating_required: string | null;
  rating_provided: string | null;
};

type DrawingType = "architectural" | "mechanical";

type Drawing = {
  id: number;
  project_id: number;
  type: DrawingType;
  file_path: string;
  upload_date: string;
};

const DRAWING_TYPES: { value: DrawingType; label: string }[] = [
  { value: "architectural", label: "Architectural" },
  { value: "mechanical", label: "Mechanical" },
];

const FIRE_PROTECTION_ITEM_TYPES: {
  value: FireProtectionItemType;
  label: string;
}[] = [
  { value: "fire_extinguisher", label: "Fire extinguisher" },
  { value: "penetration_seal", label: "Penetration seal" },
  { value: "fire_separation", label: "Fire separation" },
];

const inputClassName =
  "rounded border border-zinc-300 bg-white px-3 py-2 text-base text-zinc-900";

const SECTIONS = [
  "Rooms",
  "Doors",
  "Corridors",
  "Exits",
  "Fire Protection",
  "Drawings",
  "Compliance",
] as const;

type Section = (typeof SECTIONS)[number];

export default function ProjectDetailPage() {
  const params = useParams<{ id: string }>();
  const projectId = Number(params.id);
  const [project, setProject] = useState<Project | null>(null);
  const [activeSection, setActiveSection] = useState<Section>("Rooms");
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function fetchProject() {
      setIsLoading(true);
      setError(null);

      try {
        const response = await apiFetch(`/api/v1/projects/${projectId}`);

        if (!response.ok) {
          throw new Error(await readErrorMessage(response));
        }

        const data = (await response.json()) as Project;
        if (!cancelled) {
          setProject(data);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load project");
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    if (!Number.isNaN(projectId)) {
      fetchProject();
    }

    return () => {
      cancelled = true;
    };
  }, [projectId]);

  return (
    <main className="mx-auto w-full max-w-4xl flex-1 px-4 py-16">
      <p className="mb-4 text-sm">
        <Link href="/projects" className="text-zinc-600 underline">
          ← Back to projects
        </Link>
      </p>

      {isLoading ? (
        <p className="text-sm text-zinc-600">Loading project…</p>
      ) : error ? (
        <p className="text-sm text-red-600" role="alert">
          {error}
        </p>
      ) : project ? (
        <>
          <h1 className="mb-8 text-2xl font-semibold">{project.name}</h1>

          <div className="flex flex-col gap-6 md:flex-row">
            <nav className="flex shrink-0 flex-row flex-wrap gap-2 md:w-48 md:flex-col">
              {SECTIONS.map((section) => (
                <button
                  key={section}
                  type="button"
                  onClick={() => setActiveSection(section)}
                  className={`rounded px-3 py-2 text-left text-sm ${
                    activeSection === section
                      ? "bg-zinc-900 font-medium text-white"
                      : "bg-zinc-100 text-zinc-900 hover:bg-zinc-200"
                  }`}
                >
                  {section}
                </button>
              ))}
            </nav>

            <section className="min-h-48 flex-1 rounded border border-zinc-200 p-6">
              {activeSection === "Rooms" ? (
                <RoomsSection projectId={project.id} />
              ) : activeSection === "Doors" ? (
                <DoorsSection projectId={project.id} />
              ) : activeSection === "Corridors" ? (
                <CorridorsSection projectId={project.id} />
              ) : activeSection === "Exits" ? (
                <ExitsSection projectId={project.id} />
              ) : activeSection === "Fire Protection" ? (
                <FireProtectionSection projectId={project.id} />
              ) : activeSection === "Drawings" ? (
                <DrawingsSection projectId={project.id} />
              ) : activeSection === "Compliance" ? (
                <ComplianceSection projectId={project.id} />
              ) : (
                <>
                  <h2 className="mb-2 text-lg font-medium">{activeSection}</h2>
                  <p className="text-sm text-zinc-600">
                    {activeSection} content will go here.
                  </p>
                </>
              )}
            </section>
          </div>
        </>
      ) : null}
    </main>
  );
}

function RoomsSection({ projectId }: { projectId: number }) {
  const [rooms, setRooms] = useState<Room[]>([]);
  const [name, setName] = useState("");
  const [occupancyCategory, setOccupancyCategory] = useState("");
  const [floorArea, setFloorArea] = useState("");
  const [occupantLoad, setOccupantLoad] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const loadRooms = useCallback(async () => {
    setError(null);

    const response = await apiFetch("/api/v1/rooms");

    if (!response.ok) {
      throw new Error(await readErrorMessage(response));
    }

    const data = (await response.json()) as Room[];
    setRooms(data.filter((room) => room.project_id === projectId));
  }, [projectId]);

  useEffect(() => {
    let cancelled = false;

    async function fetchRooms() {
      setIsLoading(true);
      try {
        await loadRooms();
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load rooms");
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    fetchRooms();

    return () => {
      cancelled = true;
    };
  }, [loadRooms]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      const response = await apiFetch("/api/v1/rooms", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          project_id: projectId,
          name,
          occupancy_category: occupancyCategory,
          floor_area: Number(floorArea),
          occupant_load: Number(occupantLoad),
        }),
      });

      if (!response.ok) {
        throw new Error(await readErrorMessage(response));
      }

      setName("");
      setOccupancyCategory("");
      setFloorArea("");
      setOccupantLoad("");
      await loadRooms();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create room");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <>
      <h2 className="mb-4 text-lg font-medium">Rooms</h2>

      <form onSubmit={handleSubmit} className="mb-8 grid gap-4 sm:grid-cols-2">
        <label className="flex flex-col gap-1 text-sm">
          <span>Name</span>
          <input
            type="text"
            name="name"
            value={name}
            onChange={(event) => setName(event.target.value)}
            required
            className="rounded border border-zinc-300 bg-white px-3 py-2 text-base text-zinc-900"
          />
        </label>

        <label className="flex flex-col gap-1 text-sm">
          <span>Occupancy category</span>
          <input
            type="text"
            name="occupancy_category"
            value={occupancyCategory}
            onChange={(event) => setOccupancyCategory(event.target.value)}
            required
            className="rounded border border-zinc-300 bg-white px-3 py-2 text-base text-zinc-900"
          />
        </label>

        <label className="flex flex-col gap-1 text-sm">
          <span>Floor area</span>
          <input
            type="number"
            name="floor_area"
            value={floorArea}
            onChange={(event) => setFloorArea(event.target.value)}
            required
            min="0"
            step="any"
            className="rounded border border-zinc-300 bg-white px-3 py-2 text-base text-zinc-900"
          />
        </label>

        <label className="flex flex-col gap-1 text-sm">
          <span>Occupant load</span>
          <input
            type="number"
            name="occupant_load"
            value={occupantLoad}
            onChange={(event) => setOccupantLoad(event.target.value)}
            required
            min="0"
            step="1"
            className="rounded border border-zinc-300 bg-white px-3 py-2 text-base text-zinc-900"
          />
        </label>

        <div className="sm:col-span-2">
          <button
            type="submit"
            disabled={isSubmitting}
            className="rounded bg-zinc-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
          >
            {isSubmitting ? "Adding…" : "Add Room"}
          </button>
        </div>
      </form>

      {error ? (
        <p className="mb-4 text-sm text-red-600" role="alert">
          {error}
        </p>
      ) : null}

      {isLoading ? (
        <p className="text-sm text-zinc-600">Loading rooms…</p>
      ) : rooms.length === 0 ? (
        <p className="text-sm text-zinc-600">No rooms yet.</p>
      ) : (
        <table className="w-full border-collapse text-left text-sm">
          <thead>
            <tr className="border-b border-zinc-300">
              <th className="py-2 pr-4 font-medium">Name</th>
              <th className="py-2 pr-4 font-medium">Occupancy</th>
              <th className="py-2 pr-4 font-medium">Floor area</th>
              <th className="py-2 pr-4 font-medium">Occupant load</th>
            </tr>
          </thead>
          <tbody>
            {rooms.map((room) => (
              <tr key={room.id} className="border-b border-zinc-200">
                <td className="py-2 pr-4">{room.name}</td>
                <td className="py-2 pr-4">{room.occupancy_category}</td>
                <td className="py-2 pr-4">{room.floor_area}</td>
                <td className="py-2 pr-4">{room.occupant_load}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </>
  );
}

function DoorsSection({ projectId }: { projectId: number }) {
  const [rooms, setRooms] = useState<Room[]>([]);
  const [doors, setDoors] = useState<Door[]>([]);
  const [roomId, setRoomId] = useState("");
  const [clearWidth, setClearWidth] = useState("");
  const [fireRating, setFireRating] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const loadData = useCallback(async () => {
    setError(null);

    const [roomsResponse, doorsResponse] = await Promise.all([
      apiFetch("/api/v1/rooms"),
      apiFetch("/api/v1/doors"),
    ]);

    if (!roomsResponse.ok) {
      throw new Error(await readErrorMessage(roomsResponse));
    }

    if (!doorsResponse.ok) {
      throw new Error(await readErrorMessage(doorsResponse));
    }

    const allRooms = (await roomsResponse.json()) as Room[];
    const projectRooms = allRooms.filter((room) => room.project_id === projectId);
    const roomIds = new Set(projectRooms.map((room) => room.id));

    const allDoors = (await doorsResponse.json()) as Door[];
    const projectDoors = allDoors.filter((door) => roomIds.has(door.room_id));

    setRooms(projectRooms);
    setDoors(projectDoors);

    if (projectRooms.length > 0) {
      setRoomId((current) =>
        projectRooms.some((room) => String(room.id) === current)
          ? current
          : String(projectRooms[0].id),
      );
    } else {
      setRoomId("");
    }
  }, [projectId]);

  useEffect(() => {
    let cancelled = false;

    async function fetchData() {
      setIsLoading(true);
      try {
        await loadData();
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load doors");
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    fetchData();

    return () => {
      cancelled = true;
    };
  }, [loadData]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      const response = await apiFetch("/api/v1/doors", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          room_id: Number(roomId),
          clear_width: Number(clearWidth),
          fire_rating: fireRating.trim() === "" ? null : fireRating.trim(),
        }),
      });

      if (!response.ok) {
        throw new Error(await readErrorMessage(response));
      }

      setClearWidth("");
      setFireRating("");
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create door");
    } finally {
      setIsSubmitting(false);
    }
  }

  const roomNameById = new Map(rooms.map((room) => [room.id, room.name]));

  return (
    <>
      <h2 className="mb-4 text-lg font-medium">Doors</h2>

      {isLoading ? (
        <p className="mb-4 text-sm text-zinc-600">Loading doors…</p>
      ) : rooms.length === 0 ? (
        <p className="mb-8 text-sm text-zinc-600">
          Add a room in the Rooms section before creating doors.
        </p>
      ) : (
        <form onSubmit={handleSubmit} className="mb-8 grid gap-4 sm:grid-cols-2">
          <label className="flex flex-col gap-1 text-sm">
            <span>Room</span>
            <select
              name="room_id"
              value={roomId}
              onChange={(event) => setRoomId(event.target.value)}
              required
              className="rounded border border-zinc-300 bg-white px-3 py-2 text-base text-zinc-900"
            >
              {rooms.map((room) => (
                <option key={room.id} value={room.id}>
                  {room.name}
                </option>
              ))}
            </select>
          </label>

          <label className="flex flex-col gap-1 text-sm">
            <span>Clear width</span>
            <input
              type="number"
              name="clear_width"
              value={clearWidth}
              onChange={(event) => setClearWidth(event.target.value)}
              required
              min="0"
              step="any"
              className="rounded border border-zinc-300 bg-white px-3 py-2 text-base text-zinc-900"
            />
          </label>

          <label className="flex flex-col gap-1 text-sm sm:col-span-2">
            <span>Fire rating (optional)</span>
            <input
              type="text"
              name="fire_rating"
              value={fireRating}
              onChange={(event) => setFireRating(event.target.value)}
              className="rounded border border-zinc-300 bg-white px-3 py-2 text-base text-zinc-900"
            />
          </label>

          <div className="sm:col-span-2">
            <button
              type="submit"
              disabled={isSubmitting}
              className="rounded bg-zinc-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
            >
              {isSubmitting ? "Adding…" : "Add Door"}
            </button>
          </div>
        </form>
      )}

      {error ? (
        <p className="mb-4 text-sm text-red-600" role="alert">
          {error}
        </p>
      ) : null}

      {!isLoading && doors.length === 0 ? (
        <p className="text-sm text-zinc-600">No doors yet.</p>
      ) : !isLoading ? (
        <table className="w-full border-collapse text-left text-sm">
          <thead>
            <tr className="border-b border-zinc-300">
              <th className="py-2 pr-4 font-medium">Room</th>
              <th className="py-2 pr-4 font-medium">Clear width</th>
              <th className="py-2 pr-4 font-medium">Fire rating</th>
            </tr>
          </thead>
          <tbody>
            {doors.map((door) => (
              <tr key={door.id} className="border-b border-zinc-200">
                <td className="py-2 pr-4">
                  {roomNameById.get(door.room_id) ?? `Room ${door.room_id}`}
                </td>
                <td className="py-2 pr-4">{door.clear_width}</td>
                <td className="py-2 pr-4">{door.fire_rating ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : null}
    </>
  );
}

function CorridorsSection({ projectId }: { projectId: number }) {
  const [corridors, setCorridors] = useState<Corridor[]>([]);
  const [clearWidth, setClearWidth] = useState("");
  const [length, setLength] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const loadCorridors = useCallback(async () => {
    setError(null);

    const response = await apiFetch("/api/v1/corridors");

    if (!response.ok) {
      throw new Error(await readErrorMessage(response));
    }

    const data = (await response.json()) as Corridor[];
    setCorridors(data.filter((corridor) => corridor.project_id === projectId));
  }, [projectId]);

  useEffect(() => {
    let cancelled = false;

    async function fetchCorridors() {
      setIsLoading(true);
      try {
        await loadCorridors();
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load corridors");
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    fetchCorridors();

    return () => {
      cancelled = true;
    };
  }, [loadCorridors]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      const response = await apiFetch("/api/v1/corridors", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          project_id: projectId,
          clear_width: Number(clearWidth),
          length: Number(length),
        }),
      });

      if (!response.ok) {
        throw new Error(await readErrorMessage(response));
      }

      setClearWidth("");
      setLength("");
      await loadCorridors();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create corridor");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <>
      <h2 className="mb-4 text-lg font-medium">Corridors</h2>

      <form onSubmit={handleSubmit} className="mb-8 grid gap-4 sm:grid-cols-2">
        <label className="flex flex-col gap-1 text-sm">
          <span>Clear width</span>
          <input
            type="number"
            name="clear_width"
            value={clearWidth}
            onChange={(event) => setClearWidth(event.target.value)}
            required
            min="0"
            step="any"
            className={inputClassName}
          />
        </label>

        <label className="flex flex-col gap-1 text-sm">
          <span>Length</span>
          <input
            type="number"
            name="length"
            value={length}
            onChange={(event) => setLength(event.target.value)}
            required
            min="0"
            step="any"
            className={inputClassName}
          />
        </label>

        <div className="sm:col-span-2">
          <button
            type="submit"
            disabled={isSubmitting}
            className="rounded bg-zinc-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
          >
            {isSubmitting ? "Adding…" : "Add Corridor"}
          </button>
        </div>
      </form>

      {error ? (
        <p className="mb-4 text-sm text-red-600" role="alert">
          {error}
        </p>
      ) : null}

      {isLoading ? (
        <p className="text-sm text-zinc-600">Loading corridors…</p>
      ) : corridors.length === 0 ? (
        <p className="text-sm text-zinc-600">No corridors yet.</p>
      ) : (
        <table className="w-full border-collapse text-left text-sm">
          <thead>
            <tr className="border-b border-zinc-300">
              <th className="py-2 pr-4 font-medium">Clear width</th>
              <th className="py-2 pr-4 font-medium">Length</th>
            </tr>
          </thead>
          <tbody>
            {corridors.map((corridor) => (
              <tr key={corridor.id} className="border-b border-zinc-200">
                <td className="py-2 pr-4">{corridor.clear_width}</td>
                <td className="py-2 pr-4">{corridor.length}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </>
  );
}

function ExitsSection({ projectId }: { projectId: number }) {
  const [exits, setExits] = useState<Exit[]>([]);
  const [location, setLocation] = useState("");
  const [clearWidth, setClearWidth] = useState("");
  const [isRequiredExit, setIsRequiredExit] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const loadExits = useCallback(async () => {
    setError(null);

    const response = await apiFetch("/api/v1/exits");

    if (!response.ok) {
      throw new Error(await readErrorMessage(response));
    }

    const data = (await response.json()) as Exit[];
    setExits(data.filter((exit) => exit.project_id === projectId));
  }, [projectId]);

  useEffect(() => {
    let cancelled = false;

    async function fetchExits() {
      setIsLoading(true);
      try {
        await loadExits();
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load exits");
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    fetchExits();

    return () => {
      cancelled = true;
    };
  }, [loadExits]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      const response = await apiFetch("/api/v1/exits", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          project_id: projectId,
          location,
          clear_width: Number(clearWidth),
          is_required_exit: isRequiredExit,
        }),
      });

      if (!response.ok) {
        throw new Error(await readErrorMessage(response));
      }

      setLocation("");
      setClearWidth("");
      setIsRequiredExit(false);
      await loadExits();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create exit");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <>
      <h2 className="mb-4 text-lg font-medium">Exits</h2>

      <form onSubmit={handleSubmit} className="mb-8 grid gap-4 sm:grid-cols-2">
        <label className="flex flex-col gap-1 text-sm sm:col-span-2">
          <span>Location</span>
          <input
            type="text"
            name="location"
            value={location}
            onChange={(event) => setLocation(event.target.value)}
            required
            className={inputClassName}
          />
        </label>

        <label className="flex flex-col gap-1 text-sm">
          <span>Clear width</span>
          <input
            type="number"
            name="clear_width"
            value={clearWidth}
            onChange={(event) => setClearWidth(event.target.value)}
            required
            min="0"
            step="any"
            className={inputClassName}
          />
        </label>

        <label className="flex items-center gap-2 self-end text-sm">
          <input
            type="checkbox"
            name="is_required_exit"
            checked={isRequiredExit}
            onChange={(event) => setIsRequiredExit(event.target.checked)}
            className="h-4 w-4"
          />
          <span>Required exit</span>
        </label>

        <div className="sm:col-span-2">
          <button
            type="submit"
            disabled={isSubmitting}
            className="rounded bg-zinc-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
          >
            {isSubmitting ? "Adding…" : "Add Exit"}
          </button>
        </div>
      </form>

      {error ? (
        <p className="mb-4 text-sm text-red-600" role="alert">
          {error}
        </p>
      ) : null}

      {isLoading ? (
        <p className="text-sm text-zinc-600">Loading exits…</p>
      ) : exits.length === 0 ? (
        <p className="text-sm text-zinc-600">No exits yet.</p>
      ) : (
        <table className="w-full border-collapse text-left text-sm">
          <thead>
            <tr className="border-b border-zinc-300">
              <th className="py-2 pr-4 font-medium">Location</th>
              <th className="py-2 pr-4 font-medium">Clear width</th>
              <th className="py-2 pr-4 font-medium">Required exit</th>
            </tr>
          </thead>
          <tbody>
            {exits.map((exit) => (
              <tr key={exit.id} className="border-b border-zinc-200">
                <td className="py-2 pr-4">{exit.location}</td>
                <td className="py-2 pr-4">{exit.clear_width}</td>
                <td className="py-2 pr-4">{exit.is_required_exit ? "Yes" : "No"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </>
  );
}

function FireProtectionSection({ projectId }: { projectId: number }) {
  const [items, setItems] = useState<FireProtectionItem[]>([]);
  const [itemType, setItemType] =
    useState<FireProtectionItemType>("fire_extinguisher");
  const [location, setLocation] = useState("");
  const [ratingRequired, setRatingRequired] = useState("");
  const [ratingProvided, setRatingProvided] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const loadItems = useCallback(async () => {
    setError(null);

    const response = await apiFetch("/api/v1/fire-protection-items");

    if (!response.ok) {
      throw new Error(await readErrorMessage(response));
    }

    const data = (await response.json()) as FireProtectionItem[];
    setItems(data.filter((item) => item.project_id === projectId));
  }, [projectId]);

  useEffect(() => {
    let cancelled = false;

    async function fetchItems() {
      setIsLoading(true);
      try {
        await loadItems();
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof Error
              ? err.message
              : "Failed to load fire protection items",
          );
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    fetchItems();

    return () => {
      cancelled = true;
    };
  }, [loadItems]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      const response = await apiFetch("/api/v1/fire-protection-items", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          project_id: projectId,
          item_type: itemType,
          location,
          rating_required:
            ratingRequired.trim() === "" ? null : ratingRequired.trim(),
          rating_provided:
            ratingProvided.trim() === "" ? null : ratingProvided.trim(),
        }),
      });

      if (!response.ok) {
        throw new Error(await readErrorMessage(response));
      }

      setLocation("");
      setRatingRequired("");
      setRatingProvided("");
      await loadItems();
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Failed to create fire protection item",
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  const itemTypeLabel = (value: FireProtectionItemType) =>
    FIRE_PROTECTION_ITEM_TYPES.find((option) => option.value === value)?.label ??
    value;

  return (
    <>
      <h2 className="mb-4 text-lg font-medium">Fire Protection</h2>

      <form onSubmit={handleSubmit} className="mb-8 grid gap-4 sm:grid-cols-2">
        <label className="flex flex-col gap-1 text-sm">
          <span>Item type</span>
          <select
            name="item_type"
            value={itemType}
            onChange={(event) =>
              setItemType(event.target.value as FireProtectionItemType)
            }
            required
            className={inputClassName}
          >
            {FIRE_PROTECTION_ITEM_TYPES.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>

        <label className="flex flex-col gap-1 text-sm">
          <span>Location</span>
          <input
            type="text"
            name="location"
            value={location}
            onChange={(event) => setLocation(event.target.value)}
            required
            className={inputClassName}
          />
        </label>

        <label className="flex flex-col gap-1 text-sm">
          <span>Rating required (optional)</span>
          <input
            type="text"
            name="rating_required"
            value={ratingRequired}
            onChange={(event) => setRatingRequired(event.target.value)}
            className={inputClassName}
          />
        </label>

        <label className="flex flex-col gap-1 text-sm">
          <span>Rating provided (optional)</span>
          <input
            type="text"
            name="rating_provided"
            value={ratingProvided}
            onChange={(event) => setRatingProvided(event.target.value)}
            className={inputClassName}
          />
        </label>

        <div className="sm:col-span-2">
          <button
            type="submit"
            disabled={isSubmitting}
            className="rounded bg-zinc-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
          >
            {isSubmitting ? "Adding…" : "Add Item"}
          </button>
        </div>
      </form>

      {error ? (
        <p className="mb-4 text-sm text-red-600" role="alert">
          {error}
        </p>
      ) : null}

      {isLoading ? (
        <p className="text-sm text-zinc-600">Loading fire protection items…</p>
      ) : items.length === 0 ? (
        <p className="text-sm text-zinc-600">No fire protection items yet.</p>
      ) : (
        <table className="w-full border-collapse text-left text-sm">
          <thead>
            <tr className="border-b border-zinc-300">
              <th className="py-2 pr-4 font-medium">Type</th>
              <th className="py-2 pr-4 font-medium">Location</th>
              <th className="py-2 pr-4 font-medium">Rating required</th>
              <th className="py-2 pr-4 font-medium">Rating provided</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.id} className="border-b border-zinc-200">
                <td className="py-2 pr-4">{itemTypeLabel(item.item_type)}</td>
                <td className="py-2 pr-4">{item.location}</td>
                <td className="py-2 pr-4">{item.rating_required ?? "—"}</td>
                <td className="py-2 pr-4">{item.rating_provided ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </>
  );
}

function DrawingsSection({ projectId }: { projectId: number }) {
  const [drawings, setDrawings] = useState<Drawing[]>([]);
  const [file, setFile] = useState<File | null>(null);
  const [drawingType, setDrawingType] = useState<DrawingType>("architectural");
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const loadDrawings = useCallback(async () => {
    setError(null);

    const response = await apiFetch(`/api/v1/projects/${projectId}/drawings`);

    if (!response.ok) {
      throw new Error(await readErrorMessage(response));
    }

    const data = (await response.json()) as Drawing[];
    setDrawings(data);
  }, [projectId]);

  useEffect(() => {
    let cancelled = false;

    async function fetchDrawings() {
      setIsLoading(true);
      try {
        await loadDrawings();
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load drawings");
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    fetchDrawings();

    return () => {
      cancelled = true;
    };
  }, [loadDrawings]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file) {
      setError("Select a PDF file to upload.");
      return;
    }

    setError(null);
    setIsSubmitting(true);

    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("type", drawingType);

      const uploadResponse = await apiFetch(
        `/api/v1/projects/${projectId}/drawings`,
        {
          method: "POST",
          body: formData,
        },
      );

      if (!uploadResponse.ok) {
        throw new Error(await readErrorMessage(uploadResponse));
      }

      const drawing = (await uploadResponse.json()) as Drawing;

      const extractResponse = await apiFetch(
        `/api/v1/drawings/${drawing.id}/extract`,
        { method: "POST" },
      );

      if (!extractResponse.ok) {
        throw new Error(await readErrorMessage(extractResponse));
      }

      setFile(null);
      event.currentTarget.reset();
      await loadDrawings();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to upload drawing");
    } finally {
      setIsSubmitting(false);
    }
  }

  function drawingFileName(filePath: string): string {
    return filePath.split("/").pop() ?? filePath;
  }

  return (
    <>
      <h2 className="mb-4 text-lg font-medium">Drawings</h2>

      <form onSubmit={handleSubmit} className="mb-8 grid gap-4 sm:grid-cols-2">
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

        <label className="flex flex-col gap-1 text-sm">
          <span>Type</span>
          <select
            name="type"
            value={drawingType}
            onChange={(event) =>
              setDrawingType(event.target.value as DrawingType)
            }
            required
            className={inputClassName}
          >
            {DRAWING_TYPES.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>

        <div className="flex items-end">
          <button
            type="submit"
            disabled={isSubmitting}
            className="rounded bg-zinc-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
          >
            {isSubmitting ? "Uploading…" : "Upload Drawing"}
          </button>
        </div>
      </form>

      {error ? (
        <p className="mb-4 text-sm text-red-600" role="alert">
          {error}
        </p>
      ) : null}

      {isLoading ? (
        <p className="text-sm text-zinc-600">Loading drawings…</p>
      ) : drawings.length === 0 ? (
        <p className="text-sm text-zinc-600">No drawings yet.</p>
      ) : (
        <ul className="space-y-4">
          {drawings.map((drawing) => (
            <li
              key={drawing.id}
              className="rounded border border-zinc-200 p-4 text-sm"
            >
              <p className="font-medium text-zinc-900">
                {drawingFileName(drawing.file_path)}
              </p>
              <p className="mt-1 text-zinc-600">
                Type: {drawing.type} · Uploaded{" "}
                {new Date(drawing.upload_date).toLocaleString()}
              </p>
              <div className="mt-3 flex flex-wrap gap-4">
                <Link
                  href={`/drawings/${drawing.id}/review-rooms`}
                  className="font-medium text-zinc-900 underline"
                >
                  Review extracted rooms
                </Link>
                <Link
                  href={`/drawings/${drawing.id}/review-doors`}
                  className="font-medium text-zinc-900 underline"
                >
                  Review extracted doors
                </Link>
              </div>
            </li>
          ))}
        </ul>
      )}
    </>
  );
}

function ComplianceSection({ projectId }: { projectId: number }) {
  const [report, setReport] = useState<ComplianceReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isDownloading, setIsDownloading] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function fetchCompliance() {
      setIsLoading(true);
      setError(null);

      try {
        const response = await apiFetch(
          `/api/v1/projects/${projectId}/compliance`,
        );

        if (!response.ok) {
          throw new Error(await readErrorMessage(response));
        }

        const data = (await response.json()) as ComplianceReport;
        if (!cancelled) {
          setReport(data);
        }
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof Error ? err.message : "Failed to load compliance report",
          );
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    fetchCompliance();

    return () => {
      cancelled = true;
    };
  }, [projectId]);

  async function handleDownload() {
    setError(null);
    setIsDownloading(true);

    try {
      const response = await apiFetch(
        `/api/v1/projects/${projectId}/compliance/export`,
      );

      if (!response.ok) {
        throw new Error(await readErrorMessage(response));
      }

      const blob = await response.blob();
      const filename =
        parseContentDispositionFilename(
          response.headers.get("Content-Disposition"),
        ) ?? `compliance-report-project-${projectId}.pdf`;

      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = filename;
      anchor.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to download compliance report",
      );
    } finally {
      setIsDownloading(false);
    }
  }

  return (
    <>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-4">
        <h2 className="text-lg font-medium">Compliance</h2>
        <button
          type="button"
          onClick={handleDownload}
          disabled={isDownloading}
          className="rounded bg-zinc-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
        >
          {isDownloading ? "Downloading…" : "Download Compliance Report"}
        </button>
      </div>

      {isLoading ? (
        <p className="text-sm text-zinc-600">Loading compliance report…</p>
      ) : error ? (
        <p className="text-sm text-red-600" role="alert">
          {error}
        </p>
      ) : report ? (
        <>
          <p className="mb-6 text-sm text-zinc-600">
            <span className="font-medium text-green-700">
              {report.summary.passed} passed
            </span>
            {" · "}
            <span className="font-medium text-red-700">
              {report.summary.failed} failed
            </span>
          </p>

          {report.results.length === 0 ? (
            <p className="text-sm text-zinc-600">No rule results.</p>
          ) : (
            <ul className="space-y-4">
              {report.results.map((result) => (
                <li
                  key={result.rule_id}
                  className="rounded border border-zinc-200 p-4 text-sm"
                >
                  <div className="mb-2 flex flex-wrap items-center gap-2">
                    <span
                      className={`rounded px-2 py-0.5 text-xs font-medium ${
                        result.passed
                          ? "bg-green-100 text-green-800"
                          : "bg-red-100 text-red-800"
                      }`}
                    >
                      {result.passed ? "Pass" : "Fail"}
                    </span>
                    <span className="font-medium text-zinc-900">
                      {result.rule_id}
                    </span>
                  </div>
                  <p className="text-zinc-700">{result.message}</p>
                  {result.regulation_citation ? (
                    <p className="mt-2 text-zinc-600">
                      Citation: {result.regulation_citation}
                    </p>
                  ) : null}
                </li>
              ))}
            </ul>
          )}
        </>
      ) : null}
    </>
  );
}

type ComplianceReport = {
  project_id: number;
  generated_at: string;
  results: {
    rule_id: string;
    passed: boolean;
    message: string;
    regulation_citation: string | null;
  }[];
  summary: {
    passed: number;
    failed: number;
  };
};

function parseContentDispositionFilename(
  header: string | null,
): string | null {
  if (!header) {
    return null;
  }

  const match = header.match(/filename="([^"]+)"/);
  return match?.[1] ?? null;
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
