"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useState } from "react";

import { apiFetch } from "@/lib/api";

type Project = {
  id: number;
  name: string;
  owner_id: number;
};

export default function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const loadProjects = useCallback(async () => {
    setError(null);

    const response = await apiFetch("/api/v1/projects");

    if (!response.ok) {
      throw new Error(await readErrorMessage(response));
    }

    const data = (await response.json()) as Project[];
    setProjects(data);
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function fetchProjects() {
      setIsLoading(true);
      try {
        await loadProjects();
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load projects");
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    fetchProjects();

    return () => {
      cancelled = true;
    };
  }, [loadProjects]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      const response = await apiFetch("/api/v1/projects", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name }),
      });

      if (!response.ok) {
        throw new Error(await readErrorMessage(response));
      }

      setName("");
      await loadProjects();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create project");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="mx-auto w-full max-w-3xl flex-1 px-4 py-16">
      <h1 className="mb-8 text-2xl font-semibold">Projects</h1>

      <section className="mb-10">
        <h2 className="mb-4 text-lg font-medium">New Project</h2>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4 sm:flex-row sm:items-end">
          <label className="flex flex-1 flex-col gap-1 text-sm">
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

          <button
            type="submit"
            disabled={isSubmitting}
            className="rounded bg-zinc-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
          >
            {isSubmitting ? "Creating…" : "New Project"}
          </button>
        </form>
      </section>

      {error ? (
        <p className="mb-6 text-sm text-red-600" role="alert">
          {error}
        </p>
      ) : null}

      <section>
        <h2 className="mb-4 text-lg font-medium">Your Projects</h2>

        {isLoading ? (
          <p className="text-sm text-zinc-600">Loading projects…</p>
        ) : projects.length === 0 ? (
          <p className="text-sm text-zinc-600">No projects yet.</p>
        ) : (
          <table className="w-full border-collapse text-left text-sm">
            <thead>
              <tr className="border-b border-zinc-300">
                <th className="py-2 pr-4 font-medium">Name</th>
              </tr>
            </thead>
            <tbody>
              {projects.map((project) => (
                <tr key={project.id} className="border-b border-zinc-200">
                  <td className="py-2 pr-4">
                    <Link
                      href={`/projects/${project.id}`}
                      className="font-medium text-zinc-900 underline"
                    >
                      {project.name}
                    </Link>
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
