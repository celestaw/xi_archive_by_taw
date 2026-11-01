import type { components, paths } from "./schema";

export type Work = components["schemas"]["WorkSummary"];
export type WorkDetail = components["schemas"]["WorkDetail"];
export type WorkContext = components["schemas"]["WorkContext"];
export type RecordDate = components["schemas"]["PublicationRecord"];
export type Meta = components["schemas"]["ArchiveMeta"];
export type WorkList = components["schemas"]["WorkList"];
export type WorkQuery = NonNullable<paths["/api/v1/works"]["get"]["parameters"]["query"]>;
export type CollectionSummary = components["schemas"]["CollectionSummary"];
export type CollectionDetail = components["schemas"]["CollectionDetail"];
export type CollectionList = components["schemas"]["CollectionList"];
export type CollectionKind = "album" | "game";
export type TimelineEntry = components["schemas"]["TimelineEntry"];
export type TimelineList = components["schemas"]["TimelineList"];

export class ApiFailure extends Error {
  constructor(public status: number, message: string) { super(message); }
}

async function request<T>(path: string, signal?: AbortSignal): Promise<T> {
  const timeout = AbortSignal.timeout(10000);
  let response: Response;
  try {
    response = await fetch(`/api/v1${path}`, {
      signal: signal ? AbortSignal.any([signal, timeout]) : timeout,
      cache: "no-store", headers: { Accept: "application/json" },
    });
  } catch (error) {
    if (timeout.aborted && !signal?.aborted) throw new ApiFailure(504, "接続に時間がかかっています。もう一度お試しください。");
    throw error;
  }
  if (!response.ok) {
    const body = await response.json().catch(() => null) as components["schemas"]["ApiError"] | null;
    throw new ApiFailure(response.status, body?.error?.message ?? "記録を取得できませんでした。");
  }
  return response.json() as Promise<T>;
}

export const api = {
  meta: (signal?: AbortSignal) => request<Meta>("/meta", signal),
  timeline: (signal?: AbortSignal) => request<TimelineList>("/timeline", signal),
  works: (query: WorkQuery, signal?: AbortSignal) => {
    const params = new URLSearchParams();
    for (const [key, value] of Object.entries(query)) {
      if (value !== null && value !== undefined && value !== "") params.set(key, String(value));
    }
    return request<WorkList>(`/works?${params}`, signal);
  },
  work: (id: string, signal?: AbortSignal) => request<WorkDetail>(`/works/${encodeURIComponent(id)}`, signal),
  workContext: (id: string, signal?: AbortSignal) => request<WorkContext>(`/works/${encodeURIComponent(id)}/context`, signal),
  collections: (kind: CollectionKind, signal?: AbortSignal) => request<CollectionList>(kind === "album" ? "/albums" : "/games", signal),
  collection: (kind: CollectionKind, id: string, signal?: AbortSignal) => request<CollectionDetail>(`${kind === "album" ? "/albums" : "/games"}/${encodeURIComponent(id)}`, signal),
};

export function formatDate(record: RecordDate | null | undefined): string {
  return record?.date?.replaceAll("-", ".") ?? "日付未確認";
}
